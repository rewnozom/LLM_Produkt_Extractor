#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PromptManager.py - Klass för att hantera en samling av promptmallar

Denna modul innehåller klassen PromptManager, som hanterar lagring, inläsning,
versionshantering och optimering av promptmallar baserat på användningsstatistik.

Funktioner:
- Hantera en samling av promptmallar
- Ladda och spara promptmallar från/till filer
- Optimera promptmallar baserat på användningsstatistik
- Caching av promptsvar för prestandaoptimering
"""

import re
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from datetime import datetime
import logging
from pathlib import Path

from .PromptTemplate import PromptTemplate
from .ExtractionPrompt import ExtractionPrompt
from .ValidationPrompt import ValidationPrompt
from .CorrectionPrompt import CorrectionPrompt
from .PromptLoader import PromptLoader


class PromptManager:
    """
    Klass för att hantera en samling av promptmallar.
    
    Hanterar lagring, inläsning, versionshantering och optimering
    av promptmallar baserat på användningsstatistik.
    """

    def __init__(self, storage_dir: Union[str, Path] = None, logger: logging.Logger = None, visualizer = None):
        """
        Initierar prompthanteraren.
        
        Args:
            storage_dir: Katalog för att lagra promptmallar
            logger: Logger för att logga meddelanden
            visualizer: Visualiserare för att visa information i terminalen
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("./prompts")
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logger
        self.visualizer = visualizer
        
        # Initialisera promptsamlingar
        self.prompts: Dict[str, PromptTemplate] = {}
        self.by_tag: Dict[str, List[str]] = {}
        self.by_type: Dict[str, List[str]] = {}
        
        # Attribut för LLM-klient
        self.llm_client = None
        
        # Caching-inställningar
        self.use_cache = False
        self.cache_dir = None
        self.response_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_cache_size = 1000
        
        # Läs in befintliga promptar om katalogen finns
        self._load_existing_prompts()
    
    def set_llm_client(self, llm_client) -> None:
        """
        Ställer in LLM-klienten som används för dynamisk optimering.
        
        Args:
            llm_client: LLM-klient att använda
        """
        self.llm_client = llm_client
        if self.logger:
            self.logger.info("LLM-klient registrerad med PromptManager")
    
    def register_with_workflow(self, workflow_manager) -> None:
        """
        Registrerar prompthanteraren med arbetsflödeshanteraren för automatisk optimering
        
        Args:
            workflow_manager: Arbetsflödeshanteraren att registrera med
        """
        # Koppla prompthanteraren till arbetsflödeshanteraren
        if hasattr(workflow_manager, 'prompt_manager'):
            workflow_manager.prompt_manager = self
        
        # Registrera callback-funktioner för automatisk promptoptimering
        if hasattr(workflow_manager, 'processor') and hasattr(workflow_manager.processor, 'register_prompt_callbacks'):
            workflow_manager.processor.register_prompt_callbacks(
                self.update_usage_statistics,
                self.get_best_prompt
            )
        
        # Logga registreringen
        if self.logger:
            self.logger.info(f"Registrerade prompthanteraren med arbetsflödeshanteraren")

    def dynamic_optimize(self, extraction_type: str, sample_texts: List[str]) -> Optional[PromptTemplate]:
        """
        Dynamiskt optimerar promptmallar för en specifik extraktionstyp baserat på testdata
        
        Args:
            extraction_type: Typ av extraktion att optimera för
            sample_texts: Lista med exempeltexter att testa mot
            
        Returns:
            Optional[PromptTemplate]: Den optimerade promptmallen eller None
        """
        if not self.llm_client:
            if self.logger:
                self.logger.error("Ingen LLM-klient tillgänglig för dynamisk optimering")
            return None
        
        # Hämta alla promptmallar för denna extraktionstyp
        candidates = self.get_prompts_by_tag(extraction_type)
        if not candidates:
            if self.logger:
                self.logger.warning(f"Inga promptmallar hittades med tagg '{extraction_type}'")
            return None
        
        # Skapa varianter för testning
        test_variants = []
        for base_prompt in candidates[:2]:  # Begränsa till de två bästa basmallar för effektivitet
            # Skapa olika varianter av basmallen
            test_variants.append(base_prompt)
            
            # Lägg till förbättrade instruktioner om det är en ExtractionPrompt
            if isinstance(base_prompt, ExtractionPrompt):
                improved = base_prompt.with_improved_instructions()
                if improved not in test_variants:
                    test_variants.append(improved)
                
                # Lägg till felförebyggande
                error_prevention = base_prompt.with_error_prevention()
                if error_prevention not in test_variants:
                    test_variants.append(error_prevention)
                
                # Kombinerad variant
                combined = improved.with_error_prevention()
                if combined not in test_variants:
                    test_variants.append(combined)
        
        if self.logger:
            self.logger.info(f"Testar {len(test_variants)} promptvarianter för optimering")
        
        # Testa varje variant på exempeltexter
        best_prompt = None
        best_score = 0.0
        results = {}
        
        for prompt in test_variants:
            success_count = 0
            total_time = 0.0
            prompt_success_rate = 0.0
            
            for text in sample_texts:
                try:
                    # Formatera prompten med texten
                    formatted_prompt = prompt.format(text=text)
                    
                    # Skicka till LLM och mät tid
                    start_time = time.time()
                    response = self.llm_client.get_completion(formatted_prompt)
                    elapsed_time = time.time() - start_time
                    
                    # Kontrollera om svaret var lyckat
                    if response.successful:
                        if extraction_type == "compatibility":
                            data = self.llm_client.response_parser.parse_compatibility_data(response.text)
                            success = "relations" in data and isinstance(data["relations"], list)
                        elif extraction_type == "technical":
                            data = self.llm_client.response_parser.parse_technical_specs(response.text)
                            success = "specifications" in data and isinstance(data["specifications"], list)
                        elif extraction_type == "combined":
                            data = self.llm_client.response_parser.extract_json(response.text)
                            success = (
                                data and isinstance(data, dict) and
                                any(key in data for key in ["product", "relations", "specifications", "data_tables"])
                            )
                        else:
                            # Grundläggande framgångskontroll
                            success = len(response.text) > 50
                        
                        if success:
                            success_count += 1
                    
                    # Spåra svarstid
                    total_time += elapsed_time
                    
                    # Uppdatera promptstatistik
                    prompt.update_latency(int(elapsed_time * 1000))
                    prompt.update_success_rate(response.successful)
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Fel vid test av prompt {prompt.name}: {str(e)}")
            
            # Beräkna framgångsfrekvens och genomsnittlig svarstid
            prompt_success_rate = success_count / len(sample_texts) if sample_texts else 0
            avg_time = total_time / len(sample_texts) if sample_texts else 0
            
            # Logga resultat
            if self.logger:
                self.logger.info(
                    f"Prompt {prompt.name}: {prompt_success_rate:.2f} framgångsfrekvens, "
                    f"{avg_time:.2f}s genomsnittlig svarstid"
                )
            
            # Spara resultatet
            results[prompt.name] = {
                "prompt": prompt,
                "success_rate": prompt_success_rate,
                "avg_time": avg_time
            }
            
            # Uppdatera bästa prompt om denna är bättre
            # Prioritera framgångsfrekvens, sedan svarstid
            if prompt_success_rate > best_score or (prompt_success_rate == best_score and avg_time < results.get(best_prompt.name if best_prompt else "", {}).get("avg_time", float('inf'))):
                best_prompt = prompt
                best_score = prompt_success_rate
        
        # Spara optimeringsresultat
        if hasattr(self, 'storage_dir'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = self.storage_dir / f"optimization_results_{extraction_type}_{timestamp}.json"
            
            try:
                with open(results_file, 'w', encoding='utf-8') as f:
                    serialized_results = {
                        name: {
                            "prompt_name": r["prompt"].name,
                            "success_rate": r["success_rate"],
                            "avg_time": r["avg_time"]
                        } for name, r in results.items()
                    }
                    json.dump(serialized_results, f, ensure_ascii=False, indent=2)
                
                if self.logger:
                    self.logger.info(f"Sparade optimeringsresultat till {results_file}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Kunde inte spara optimeringsresultat: {str(e)}")
        
        # Returnera den bästa promptmallen
        if best_prompt and self.logger:
            self.logger.info(f"Bästa prompt för {extraction_type}: {best_prompt.name} med framgångsfrekvens {best_score:.2f}")
        
        return best_prompt

    def setup_caching(self, cache_dir: Union[str, Path] = None, max_cache_size: int = 1000) -> None:
        """
        Konfigurerar caching för promptsvar
        
        Args:
            cache_dir: Katalog för att spara cachefiler
            max_cache_size: Maximalt antal cachade svar att behålla i minnet
        """
        self.use_cache = True
        self.cache_dir = Path(cache_dir) if cache_dir else (self.storage_dir / "cache" if hasattr(self, 'storage_dir') else Path("./prompt_cache"))
        self.max_cache_size = max_cache_size
        self.response_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Skapa cache-katalog
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Ladda existerande cache
        self._load_cache()
        
        if self.logger:
            self.logger.info(f"Konfigurerade promptcaching i {self.cache_dir} (max {max_cache_size} poster)")

    def _load_cache(self) -> None:
        """Laddar existerande cache från disk"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            loaded_count = 0
            
            for cache_file in cache_files[:self.max_cache_size]:  # Ladda högst max_cache_size filer
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    # Lägg till i minnes-cache
                    prompt_hash = cache_file.stem
                    self.response_cache[prompt_hash] = cache_data
                    loaded_count += 1
                    
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Kunde inte ladda cachefil {cache_file}: {str(e)}")
            
            if self.logger:
                self.logger.info(f"Laddade {loaded_count} cacheposter från disk")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid laddning av cache: {str(e)}")



    def get_cached_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Hämtar ett cachat svar för en prompt
        
        Args:
            prompt: Prompten att hämta svar för
            
        Returns:
            Optional[Dict[str, Any]]: Det cachade svaret eller None om inget hittades
        """
        if not self.use_cache:
            return None
        
        # Beräkna hash för prompten
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Kontrollera om svaret finns i minnes-cache
        if prompt_hash in self.response_cache:
            self.cache_hits += 1
            
            if self.logger:
                self.logger.debug(f"Cache-träff för prompt_hash {prompt_hash[:8]}")
            
            return self.response_cache[prompt_hash]
        
        # Kontrollera om svaret finns på disk
        cache_file = self.cache_dir / f"{prompt_hash}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Lägg till i minnes-cache
                self.response_cache[prompt_hash] = cache_data
                
                # Ta bort äldsta posten om cache är full
                if len(self.response_cache) > self.max_cache_size:
                    oldest_key = next(iter(self.response_cache))
                    del self.response_cache[oldest_key]
                
                self.cache_hits += 1
                
                if self.logger:
                    self.logger.debug(f"Disk cache-träff för prompt_hash {prompt_hash[:8]}")
                
                return cache_data
            
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Kunde inte läsa cachefil {cache_file}: {str(e)}")
        
        self.cache_misses += 1
        return None

    def cache_response(self, prompt: str, response: Dict[str, Any]) -> None:
        """
        Cachar ett svar för en prompt
        
        Args:
            prompt: Prompten att cacha svar för
            response: Svaret att cacha
        """
        if not self.use_cache:
            return
        
        # Beräkna hash för prompten
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Lägg till i minnes-cache
        self.response_cache[prompt_hash] = response
        
        # Ta bort äldsta posten om cache är full
        if len(self.response_cache) > self.max_cache_size:
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        # Spara till disk
        cache_file = self.cache_dir / f"{prompt_hash}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            
            if self.logger:
                self.logger.debug(f"Cachade svar för prompt_hash {prompt_hash[:8]}")
        
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Kunde inte spara cachefil {cache_file}: {str(e)}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Hämtar statistik för cachen
        
        Returns:
            Dict[str, Any]: Statistik för cachen
        """
        if not self.use_cache:
            return {"enabled": False}
        
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            "enabled": True,
            "cache_size": len(self.response_cache),
            "max_cache_size": self.max_cache_size,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }

    def _load_existing_prompts(self) -> None:
        """Läser in alla befintliga promptmallar från YAML-filer."""
        if not self.storage_dir.exists():
            return
        
        # Ladda alla promptar från promptkatalogen
        try:
            loaded_prompts = PromptLoader.load_prompts_from_directory(self.storage_dir, recursive=True, logger=self.logger)
            
            # Lägg till i promptsamlingen
            for name, prompt in loaded_prompts.items():
                self.add_prompt(prompt)
                
            if self.logger:
                self.logger.info(f"Laddade {len(loaded_prompts)} promptmallar från {self.storage_dir}")
                
            # Ladda fördefinierade promptmallar
            default_prompts = PromptLoader.load_default_prompts(self.logger)
            
            # Lägg till fördefinierade promptar i samlingen
            for name, prompt in default_prompts.items():
                if name not in self.prompts:
                    self.add_prompt(prompt)
                    if self.logger:
                        self.logger.info(f"Lade till fördefinierad prompt {name}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid laddning av befintliga promptmallar: {str(e)}")
    
    def add_prompt(self, prompt: PromptTemplate) -> None:
        """
        Lägger till en promptmall i samlingen.
        
        Args:
            prompt: Promptmallen att lägga till
        """
        # Lägg till i huvudsamlingen
        self.prompts[prompt.name] = prompt
        
        # Lägg till i tag-index
        for tag in prompt.tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = []
            if prompt.name not in self.by_tag[tag]:
                self.by_tag[tag].append(prompt.name)
        
        # Lägg till i typindex
        prompt_type = self._get_prompt_type(prompt)
        if prompt_type not in self.by_type:
            self.by_type[prompt_type] = []
        if prompt.name not in self.by_type[prompt_type]:
            self.by_type[prompt_type].append(prompt.name)
    
    def _get_prompt_type(self, prompt: PromptTemplate) -> str:
        """
        Bestämmer typen av promptmall.
        
        Args:
            prompt: Promptmallen att klassificera
            
        Returns:
            str: Typen av promptmall
        """
        if isinstance(prompt, ExtractionPrompt):
            return f"extraction_{prompt.extraction_type}"
        elif isinstance(prompt, ValidationPrompt):
            return "validation"
        elif isinstance(prompt, CorrectionPrompt):
            return "correction"
        else:
            return "general"
    
    def get_prompt(self, name: str) -> Optional[PromptTemplate]:
        """
        Hämtar en promptmall med ett specifikt namn.
        
        Args:
            name: Namnet på promptmallen
            
        Returns:
            Optional[PromptTemplate]: Promptmallen om den finns, annars None
        """
        return self.prompts.get(name)
    
    def get_prompts_by_tag(self, tag: str) -> List[PromptTemplate]:
        """
        Hämtar alla promptmallar med en specifik tagg.
        
        Args:
            tag: Taggen att söka efter
            
        Returns:
            List[PromptTemplate]: Lista med matchande promptmallar
        """
        prompt_names = self.by_tag.get(tag, [])
        return [self.prompts[name] for name in prompt_names if name in self.prompts]
    
    def get_prompts_by_type(self, prompt_type: str) -> List[PromptTemplate]:
        """
        Hämtar alla promptmallar av en specifik typ.
        
        Args:
            prompt_type: Typen att söka efter
            
        Returns:
            List[PromptTemplate]: Lista med matchande promptmallar
        """
        prompt_names = self.by_type.get(prompt_type, [])
        return [self.prompts[name] for name in prompt_names if name in self.prompts]
    
    def save_prompt(self, prompt: PromptTemplate) -> Path:
        """
        Sparar en promptmall till fil.
        
        Args:
            prompt: Promptmallen att spara
            
        Returns:
            Path: Sökväg till den sparade filen
        """
        # Bestäm katalog baserat på prompttyp
        if isinstance(prompt, ExtractionPrompt):
            subdir = self.storage_dir / prompt.extraction_type
        elif isinstance(prompt, ValidationPrompt):
            subdir = self.storage_dir / "validation"
        elif isinstance(prompt, CorrectionPrompt):
            subdir = self.storage_dir / "corrections"
        else:
            subdir = self.storage_dir
        
        # Skapa katalogen om den inte finns
        subdir.mkdir(exist_ok=True, parents=True)
        
        # Spara prompten
        file_path = PromptLoader.save_prompt_to_file(prompt, subdir, override=True, logger=self.logger)
        
        if not file_path:
            # Om det inte gick att spara, försök att spara i huvudkatalogen istället
            file_path = PromptLoader.save_prompt_to_file(prompt, self.storage_dir, override=True, logger=self.logger)
        
        # Uppdatera samlingen om prompten är ny eller modifierad
        self.add_prompt(prompt)
        
        return file_path
    
    def save_all(self) -> List[Path]:
        """
        Sparar alla promptmallar i samlingen.
        
        Returns:
            List[Path]: Lista med sökvägar till sparade filer
        """
        saved_paths = []
        for prompt in self.prompts.values():
            path = self.save_prompt(prompt)
            if path:
                saved_paths.append(path)
        
        if self.logger:
            self.logger.info(f"Sparade {len(saved_paths)} av {len(self.prompts)} promptmallar")
        
        return saved_paths
    
    def delete_prompt(self, name: str) -> bool:
        """
        Tar bort en promptmall från samlingen och filsystemet.
        
        Args:
            name: Namnet på promptmallen att ta bort
            
        Returns:
            bool: True om den togs bort, False annars
        """
        if name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Försökte ta bort okänd prompt: {name}")
            return False
        
        # Ta bort från samlingen
        prompt = self.prompts.pop(name)
        
        # Ta bort från taggar
        for tag in prompt.tags:
            if tag in self.by_tag and name in self.by_tag[tag]:
                self.by_tag[tag].remove(name)
        
        # Ta bort från typer
        prompt_type = self._get_prompt_type(prompt)
        if prompt_type in self.by_type and name in self.by_type[prompt_type]:
            self.by_type[prompt_type].remove(name)
        
        # Bestäm katalog baserat på prompttyp
        if isinstance(prompt, ExtractionPrompt):
            subdir = self.storage_dir / prompt.extraction_type
        elif isinstance(prompt, ValidationPrompt):
            subdir = self.storage_dir / "validation"
        elif isinstance(prompt, CorrectionPrompt):
            subdir = self.storage_dir / "corrections"
        else:
            subdir = self.storage_dir
        
        # Ta bort från filsystemet
        safe_name = re.sub(r'[^\w\-_]', '_', name)
        version = prompt.version.replace('.', '_')
        filename = f"{safe_name}_v{version}.yaml"
        file_path = subdir / filename
        
        if file_path.exists():
            try:
                file_path.unlink()
                if self.logger:
                    self.logger.info(f"Tog bort promptfil {file_path}")
                return True
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Kunde inte ta bort promptfil {file_path}: {str(e)}")
                return False
        else:
            # Prompten finns inte på disk, men vi har ändå tagit bort den från samlingen
            if self.logger:
                self.logger.warning(f"Promptfil {file_path} hittades inte vid borttagning")
            return True
    
    def update_usage_statistics(self, name: str, success: bool, latency_ms: int) -> None:
        """
        Uppdaterar användningsstatistik för en promptmall.
        
        Args:
            name: Namnet på promptmallen
            success: Om användningen var framgångsrik
            latency_ms: Svarstid i millisekunder
        """
        if name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Försökte uppdatera statistik för okänd prompt: {name}")
            return
        
        prompt = self.prompts[name]
        prompt.update_success_rate(success)
        prompt.update_latency(latency_ms)
        prompt.last_modified = datetime.now()
        
        # Spara den uppdaterade prompten
        self.save_prompt(prompt)
        
        if self.logger:
            self.logger.debug(f"Uppdaterade användningsstatistik för {name}: success={success}, latency={latency_ms}ms")
    
    def get_best_prompt(self, tags: List[str], min_success_rate: float = 0.7) -> Optional[PromptTemplate]:
        """
        Hämtar den bästa promptmallen baserat på taggar och framgångsfrekvens.
        
        Args:
            tags: Lista med taggar att matcha
            min_success_rate: Minsta acceptabla framgångsfrekvens
            
        Returns:
            Optional[PromptTemplate]: Den bästa promptmallen eller None om ingen hittades
        """
        candidates = []
        
        # Hitta promptar som matchar alla angivna taggar
        for name, prompt in self.prompts.items():
            if all(tag in prompt.tags for tag in tags) and prompt.success_rate >= min_success_rate:
                candidates.append(prompt)
        
        if not candidates:
            if self.logger:
                self.logger.warning(f"Inga lämpliga promptar hittades med taggar {tags} och min_success_rate={min_success_rate}")
            return None
        
        # Sortera efter framgångsfrekvens (högre bättre)
        candidates.sort(key=lambda p: p.success_rate, reverse=True)
        
        if self.logger:
            self.logger.debug(f"Bästa prompt för {tags}: {candidates[0].name} (framgångsfrekvens: {candidates[0].success_rate:.2f})")
        
        return candidates[0]
    
    def create_variant(self, base_name: str, variant_suffix: str, modifications: Callable[[PromptTemplate], PromptTemplate]) -> Optional[PromptTemplate]:
        """
        Skapar en variant av en befintlig promptmall.
        
        Args:
            base_name: Namnet på baspromptmallen
            variant_suffix: Suffix för den nya variantens namn
            modifications: Funktion som tar en promptmall och returnerar en modifierad version
            
        Returns:
            Optional[PromptTemplate]: Den nya varianten eller None om basen inte hittades
        """
        if base_name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Kunde inte skapa variant: basprompt {base_name} hittades inte")
            return None
        
        base_prompt = self.prompts[base_name]
        
        try:
            # Skapa varianten
            variant = modifications(base_prompt)
            
            # Uppdatera namn och version
            variant.name = f"{base_name}_{variant_suffix}"
            variant.version = f"{base_prompt.version}+{variant_suffix[:3]}"
            
            # Lägg till i samlingen
            self.add_prompt(variant)
            
            # Spara till fil
            self.save_prompt(variant)
            
            if self.logger:
                self.logger.info(f"Skapade variant {variant.name} baserad på {base_name}")
            
            return variant
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid skapande av variant av {base_name}: {str(e)}")
            return None
    
    def list_prompts(self, filter_tag: str = None) -> List[Dict[str, Any]]:
        """
        Listar alla promptmallar i samlingen.
        
        Args:
            filter_tag: Filtrera på tagg om angiven
            
        Returns:
            List[Dict[str, Any]]: Lista med information om promptmallar
        """
        result = []
        
        prompts_to_list = self.prompts.values()
        if filter_tag:
            prompts_to_list = self.get_prompts_by_tag(filter_tag)
        
        for prompt in prompts_to_list:
            result.append({
                "name": prompt.name,
                "description": prompt.description,
                "version": prompt.version,
                "tags": prompt.tags,
                "type": self._get_prompt_type(prompt),
                "usage_count": prompt.usage_count,
                "success_rate": prompt.success_rate,
                "average_latency_ms": prompt.average_latency_ms
            })
        
        return result
    
    def compare_prompt_versions(self, base_name: str) -> Dict[str, Any]:
        """
        Jämför olika versioner av en promptmall
        
        Args:
            base_name: Basnamn för promptmallar att jämföra
            
        Returns:
            Dict[str, Any]: Jämförelseresultat
        """
        # Hitta alla promptmallar med samma basnamn
        related_prompts = {}
        
        for name, prompt in self.prompts.items():
            if name == base_name or name.startswith(base_name + "_"):
                related_prompts[name] = prompt
        
        if not related_prompts:
            return {"error": f"Inga promptmallar hittades med basnamn {base_name}"}
        
        # Jämför versioner
        results = {
            "base_name": base_name,
            "version_count": len(related_prompts),
            "versions": {}
        }
        
        for name, prompt in related_prompts.items():
            # Hämta unika taggar för denna version
            unique_tags = []
            for tag in prompt.tags:
                is_unique = True
                for other_name, other_prompt in related_prompts.items():
                    if other_name != name and tag in other_prompt.tags:
                        is_unique = False
                        break
                
                if is_unique:
                    unique_tags.append(tag)
            
            # Samla information om versionen
            version_info = {
                "version": prompt.version,
                "usage_count": prompt.usage_count,
                "success_rate": prompt.success_rate,
                "average_latency_ms": prompt.average_latency_ms,
                "creation_time": prompt.creation_time.isoformat(),
                "last_modified": prompt.last_modified.isoformat(),
                "unique_tags": unique_tags
            }
            
            results["versions"][name] = version_info
        
        # Bestäm bästa version baserat på framgångsfrekvens
        best_version = max(results["versions"].items(), key=lambda x: x[1]["success_rate"])
        results["best_version"] = {
            "name": best_version[0],
            "success_rate": best_version[1]["success_rate"]
        }
        
        # Bestäm snabbaste version baserat på svarstid
        fastest_version = min(results["versions"].items(), key=lambda x: x[1]["average_latency_ms"] if x[1]["average_latency_ms"] > 0 else float('inf'))
        results["fastest_version"] = {
            "name": fastest_version[0],
            "average_latency_ms": fastest_version[1]["average_latency_ms"]
        }
        
        return results
    
    def optimize_prompt(self, name: str) -> Optional[PromptTemplate]:
        """
        Optimerar en promptmall baserat på användningsstatistik och bästa praxis.
        
        Args:
            name: Namnet på promptmallen att optimera
            
        Returns:
            Optional[PromptTemplate]: Den optimerade promptmallen eller None om optimering inte var möjlig
        """
        if name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Kunde inte optimera: prompt {name} hittades inte")
            return None
        
        prompt = self.prompts[name]
        
        try:
            # Optimera olika typer av promptar
            if isinstance(prompt, ExtractionPrompt):
                optimized = self._optimize_extraction_prompt(prompt)
            elif isinstance(prompt, ValidationPrompt):
                optimized = self._optimize_validation_prompt(prompt)
            elif isinstance(prompt, CorrectionPrompt):
                optimized = self._optimize_correction_prompt(prompt)
            else:
                optimized = self._optimize_general_prompt(prompt)
            
            if optimized is not prompt:  # Om prompten faktiskt ändrades
                optimized.name = f"{prompt.name}_optimized"
                optimized.version = f"{prompt.version}+opt"
                optimized.tags.append("optimized")
                optimized.description = f"{prompt.description} (optimerad)"
                
                # Lägg till i samlingen
                self.add_prompt(optimized)
                
                # Spara till fil
                self.save_prompt(optimized)
                
                if self.logger:
                    self.logger.info(f"Optimerade prompt {name} till {optimized.name}")
                
                return optimized
            else:
                if self.logger:
                    self.logger.info(f"Ingen optimering behövdes för {name}")
                return prompt
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid optimering av prompt {name}: {str(e)}")
            return None
    
    def _optimize_extraction_prompt(self, prompt: ExtractionPrompt) -> ExtractionPrompt:
        """
        Optimerar en extraktionsprompt.
        
        Args:
            prompt: Promptmallen att optimera
            
        Returns:
            ExtractionPrompt: Den optimerade promptmallen
        """
        # Börja med att förbättra instruktionerna
        optimized = prompt.with_improved_instructions()
        
        # Lägg till felförebyggande tips om de inte redan finns
        if "error_prevention" not in prompt.tags:
            optimized = optimized.with_error_prevention()
        
        # Anpassa för specifika scheman baserat på erfarenhet
        if "product" in prompt.schema:
            optimized = optimized.with_instruction(
                "Var mycket noggrann med produktidentifiering - extrahera endast information som faktiskt finns i texten och utelämna fält som inte nämns uttryckligen."
            )
        
        if "relations" in prompt.schema:
            # Förbättra kompatibilitetsprompt
            optimized = optimized.with_instruction(
                "Var mycket specifik med relationstypen och använd gärna exakta fraser som 'passar till', 'ersätter', 'kräver' osv."
            )
        
        if "specifications" in prompt.schema:
            # Förbättra teknisk prompt
            optimized = optimized.with_instruction(
                "Separera alltid värde och enhet, t.ex. för 'höjd: 10cm' ange raw_value='10cm', value=10, unit='cm'"
            )
        
        if "data_tables" in prompt.schema:
            # Förbättra datatabellprompt
            optimized = optimized.with_instruction(
                "Extrahera datatabeller noggrant rad för rad och behåll den exakta strukturen och innehållet från originaltabellen."
            )
        
        if "compatible_products" in prompt.schema:
            # Förbättra FAQ-prompt
            optimized = optimized.with_instruction(
                "För artikelnummer, ange alltid både leverantör och nummer om båda finns tillgängliga"
            )
        
        return optimized
    
    def _optimize_validation_prompt(self, prompt: ValidationPrompt) -> ValidationPrompt:
        """
        Optimerar en valideringsprompt.
        
        Args:
            prompt: Promptmallen att optimera
            
        Returns:
            ValidationPrompt: Den optimerade promptmallen
        """
        # Lägg till ytterligare generella valideringsregler
        additional_rules = [
            "Kontrollera att alla nödvändiga fält finns och har korrekta värdetyper",
            "Verifiera att numeriska värden är rimliga och har korrekta enheter",
            "Kontrollera att JSON-strukturen är valid och korrekt nästlad",
            "Verifiera att tomma sektioner är helt utelämnade, inte inkluderade som tomma objekt eller listor"
        ]
        
        # Förbättra med bättre feldetektering
        return prompt.with_specific_schema({}).with_error_detection()
    
    def _optimize_correction_prompt(self, prompt: CorrectionPrompt) -> CorrectionPrompt:
        """
        Optimerar en korrigeringsprompt.
        
        Args:
            prompt: Promptmallen att optimera
            
        Returns:
            CorrectionPrompt: Den optimerade promptmallen
        """
        # Lägg till ytterligare feltyper
        additional_error_types = {
            "inconsistent_format": "Data är inte konsekvent formaterad genom hela svaret",
            "invalid_data_type": "Datatyper i svaret matchar inte det förväntade (t.ex. text istället för nummer)",
            "missing_section": "En hel sektion som borde finnas baserat på innehållet saknas",
            "empty_section": "En sektion är tom istället för att vara helt utelämnad",
            "unstructured_data": "Information är inte korrekt strukturerad enligt schemat"
        }
        
        # Kombinera befintliga och nya feltyper
        combined_error_types = {**prompt.error_types, **additional_error_types}
        
        # Skapa optimerad prompt med förbättrad guidning
        optimized = CorrectionPrompt(
            template=prompt.template,
            error_types=combined_error_types,
            name=prompt.name,
            description=prompt.description,
            version=prompt.version,
            tags=prompt.tags
        )
        
        # Lägg till vägledning
        guidance_text = """
1. Läs det ursprungliga svaret noggrant och identifiera alla fel
2. Fokusera på strukturella problem som saknade eller felaktiga fält
3. Säkerställ att all information från originaltexten är korrekt extraherad
4. Åtgärda felaktiga datatyper eller formatering
5. Kontrollera att ingen korrekt information går förlorad vid korrigeringen
6. Validera att din korrigerade JSON följer det begärda formatet exakt
7. Utelämna helt tomma sektioner istället för att inkludera dem som tomma objekt eller listor
"""
        
        return optimized.with_guidance(guidance_text)
    
    def _optimize_general_prompt(self, prompt: PromptTemplate) -> PromptTemplate:
        """
        Optimerar en generell promptmall.
        
        Args:
            prompt: Promptmallen att optimera
            
        Returns:
            PromptTemplate: Den optimerade promptmallen
        """
        # Identifiera förbättringsmöjligheter i mallen
        template = prompt.template
        
        # Förtydliga instruktioner
        if "du ska" in template.lower() or "din uppgift är" in template.lower():
            template = template.replace(
                "din uppgift är att:",
                "din uppgift är att (följ dessa instruktioner exakt):"
            )
        
        # Lägg till uppmaning att vara noggrann
        if "var noggrann" not in template.lower():
            insertion_point = template.find("\n\n", len(template) // 2)
            if insertion_point > 0:
                template = template[:insertion_point] + "\n\nVar mycket noggrann i din analys." + template[insertion_point:]
        
        # Förbättra instruktioner om JSON-format om det verkar handla om JSON
        if "json" in template.lower() and "format" in template.lower():
            if "```json" not in template:
                json_instruction_pos = template.lower().find("json-format")
                if json_instruction_pos > 0:
                    template = template[:json_instruction_pos] + \
                        "JSON-format. Var särskilt noggrann med att följa exakt format, med korrekta datatyper och struktur.\n\n```json\n{example_json}\n```\n\n" + \
                        template[json_instruction_pos:]
        
        # Skapa en optimerad version
        optimized = PromptTemplate(
            template,
            prompt.name,
            prompt.description,
            prompt.version,
            prompt.tags
        )
        
        return optimized
    





    def merge_prompts(self, primary_name: str, secondary_name: str, merged_name: str = None) -> Optional[PromptTemplate]:
        """
        Kombinerar två promptmallar till en ny.
        
        Args:
            primary_name: Namnet på den primära promptmallen
            secondary_name: Namnet på den sekundära promptmallen
            merged_name: Namn för den kombinerade promptmallen (valfritt)
            
        Returns:
            Optional[PromptTemplate]: Den kombinerade promptmallen eller None om någon inte hittades
        """
        # Kontrollera att båda promptarna finns
        if primary_name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Kunde inte kombinera promptar: {primary_name} hittades inte")
            return None
            
        if secondary_name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Kunde inte kombinera promptar: {secondary_name} hittades inte")
            return None
        
        try:
            primary = self.prompts[primary_name]
            secondary = self.prompts[secondary_name]
            
            # Använd standardnamn om inget anges
            if not merged_name:
                merged_name = f"{primary_name}_merged_{secondary_name.split('_')[-1]}"
            
            # Kombinera mallar
            primary_parts = primary.template.split("---\n{text}\n---")
            secondary_parts = secondary.template.split("---\n{text}\n---")
            
            # Ta instruktioner från båda
            if len(primary_parts) > 1 and len(secondary_parts) > 1:
                instructions = primary_parts[0]
                
                # Extrahera ytterligare instruktioner från sekundär mall
                additional_instructions = []
                for line in secondary_parts[0].split("\n"):
                    if line.strip() and "din uppgift är att:" not in line.lower() and "du är en expert" not in line.lower():
                        additional_instructions.append(line)
                
                # Lägg till ytterligare instruktioner
                if additional_instructions:
                    instructions += "\n\nYTTERLIGARE INSTRUKTIONER:\n" + "\n".join(additional_instructions)
                
                merged_template = instructions + "---\n{text}\n---"
            else:
                # Om mallen inte följer text-format med separatorer
                # Försök kombinera på ett smart sätt genom att kombinera bitar
                
                # Hitta JSON-exempel i båda mallarna
                primary_json_start = primary.template.find("```json")
                secondary_json_start = secondary.template.find("```json")
                
                if primary_json_start > 0 and secondary_json_start > 0:
                    # Kombinera instruktioner från båda, men använd JSON-exemplet från primär
                    primary_intro = primary.template[:primary_json_start].strip()
                    secondary_intro = secondary.template[:secondary_json_start].strip()
                    
                    # Kombinera introduktioner
                    combined_intro = primary_intro + "\n\n" + secondary_intro
                    
                    # Hitta JSON-exemplet från primär
                    primary_json_end = primary.template.find("```", primary_json_start + 6)
                    if primary_json_end > 0:
                        primary_json = primary.template[primary_json_start:primary_json_end+3]
                        
                        # Kombinera intro, JSON och avslutande text
                        primary_outro = primary.template[primary_json_end+3:].strip()
                        
                        # Skapa den kombinerade mallen
                        merged_template = combined_intro + "\n\n" + primary_json + "\n\n" + primary_outro
                    else:
                        # Fallback om vi inte kan hitta slutet på JSON
                        merged_template = combined_intro + "\n\n" + primary.template[primary_json_start:]
                else:
                    # Ingen JSON-markup, kombinera bara mallarna
                    merged_template = primary.template + "\n\n" + "YTTERLIGARE INSTRUKTIONER FRÅN SEKUNDÄR MALL:\n" + secondary.template
            
            # Skapa kombinerade taggar
            merged_tags = list(set(primary.tags + secondary.tags))
            
            # Skapa kombinerad beskrivning
            merged_description = f"Kombination av {primary.description} och {secondary.description}"
            
            # Hantera specialfall baserat på prompttyp
            if isinstance(primary, ExtractionPrompt) and isinstance(secondary, ExtractionPrompt):
                # Kombinera scheman
                combined_schema = {**primary.schema, **secondary.schema}
                # Behåll den primära extraktionstypen om de är olika
                extraction_type = primary.extraction_type if primary.extraction_type != secondary.extraction_type else primary.extraction_type
                
                # Skapa den kombinerade promptmallen
                merged_prompt = ExtractionPrompt(
                    template=merged_template,
                    schema=combined_schema,
                    name=merged_name,
                    description=merged_description,
                    version=f"{primary.version}+{secondary.version}",
                    tags=merged_tags,
                    extraction_type=extraction_type
                )
            elif isinstance(primary, ValidationPrompt) and isinstance(secondary, ValidationPrompt):
                # Kombinera valideringsregler
                combined_rules = list(set(primary.validation_rules + secondary.validation_rules))
                
                # Skapa den kombinerade promptmallen
                merged_prompt = ValidationPrompt(
                    template=merged_template,
                    validation_rules=combined_rules,
                    name=merged_name,
                    description=merged_description,
                    version=f"{primary.version}+{secondary.version}",
                    tags=merged_tags
                )
            elif isinstance(primary, CorrectionPrompt) and isinstance(secondary, CorrectionPrompt):
                # Kombinera feltyper
                combined_error_types = {**primary.error_types, **secondary.error_types}
                
                # Skapa den kombinerade promptmallen
                merged_prompt = CorrectionPrompt(
                    template=merged_template,
                    error_types=combined_error_types,
                    name=merged_name,
                    description=merged_description,
                    version=f"{primary.version}+{secondary.version}",
                    tags=merged_tags
                )
            else:
                # Generell kombination för blandade typer
                merged_prompt = PromptTemplate(
                    template=merged_template,
                    name=merged_name,
                    description=merged_description,
                    version=f"{primary.version}+{secondary.version}",
                    tags=merged_tags
                )
            
            # Lägg till i samlingen
            self.add_prompt(merged_prompt)
            
            # Spara till fil
            self.save_prompt(merged_prompt)
            
            if self.logger:
                self.logger.info(f"Skapade kombinerad prompt {merged_name} från {primary_name} och {secondary_name}")
            
            return merged_prompt
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid kombination av promptar {primary_name} och {secondary_name}: {str(e)}")
            return None
    
    def visualize_prompt_performance(self, visualizer=None) -> None:
        """
        Visualiserar prestanda för promptmallar
        
        Args:
            visualizer: Visualiseraren att använda
        """
        if not visualizer:
            visualizer = self.visualizer
            
        if not visualizer:
            if self.logger:
                self.logger.error("Ingen visualiserare tillgänglig för att visa promptprestanda")
            return
        
        # Samla statistik grupperad efter taggar
        tag_stats = {}
        
        for prompt in self.prompts.values():
            for tag in prompt.tags:
                if tag not in tag_stats:
                    tag_stats[tag] = {
                        "count": 0,
                        "success_rate_sum": 0,
                        "latency_sum": 0,
                        "usage_count_sum": 0,
                        "prompts": []
                    }
                
                tag_stats[tag]["count"] += 1
                tag_stats[tag]["success_rate_sum"] += prompt.success_rate
                tag_stats[tag]["latency_sum"] += prompt.average_latency_ms
                tag_stats[tag]["usage_count_sum"] += prompt.usage_count
                tag_stats[tag]["prompts"].append(prompt.name)
        
        # Skapa tabelldata
        headers = ["Tagg", "Antal", "Framgångsfrekvens", "Genomsnittlig svarstid", "Användning"]
        rows = []
        
        for tag, stats in tag_stats.items():
            avg_success_rate = stats["success_rate_sum"] / stats["count"] if stats["count"] > 0 else 0
            avg_latency = stats["latency_sum"] / stats["count"] if stats["count"] > 0 else 0
            
            rows.append([
                tag,
                stats["count"],
                f"{avg_success_rate:.2f}",
                f"{avg_latency:.0f} ms",
                stats["usage_count_sum"]
            ])
        
        # Sortera efter användning (högst först)
        rows.sort(key=lambda x: int(x[4]), reverse=True)
        
        # Visa tabell
        visualizer.display_table(headers, rows, "Promptprestanda per tagg")
        
        # Visa bästa promptar
        best_prompts = []
        for prompt in sorted(self.prompts.values(), key=lambda p: p.success_rate, reverse=True)[:5]:
            best_prompts.append([
                prompt.name,
                ", ".join(prompt.tags),
                f"{prompt.success_rate:.2f}",
                f"{prompt.average_latency_ms:.0f} ms",
                prompt.usage_count
            ])
        
        if best_prompts:
            visualizer.display_table(
                ["Namn", "Taggar", "Framgångsfrekvens", "Svarstid", "Användning"],
                best_prompts,
                "5 bästa promptar"
            )
        
        # Visa mest använda promptar
        most_used_prompts = []
        for prompt in sorted(self.prompts.values(), key=lambda p: p.usage_count, reverse=True)[:5]:
            if prompt.usage_count > 0:
                most_used_prompts.append([
                    prompt.name,
                    ", ".join(prompt.tags),
                    f"{prompt.success_rate:.2f}",
                    f"{prompt.average_latency_ms:.0f} ms",
                    prompt.usage_count
                ])
        
        if most_used_prompts:
            visualizer.display_table(
                ["Namn", "Taggar", "Framgångsfrekvens", "Svarstid", "Användning"],
                most_used_prompts,
                "5 mest använda promptar"
            )
        
        # Visa prompt-typer
        type_stats = {}
        for prompt_type, prompts in self.by_type.items():
            type_stats[prompt_type] = len(prompts)
        
        type_data = []
        for prompt_type, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
            type_data.append([prompt_type, count])
        
        if type_data:
            visualizer.display_table(
                ["Prompttyp", "Antal"],
                type_data,
                "Prompttyper"
            )
        
        # Visualisera cache-statistik om tillgänglig
        if self.use_cache:
            cache_stats = self.get_cache_stats()
            
            try:
                hit_rate_percent = cache_stats.get('hit_rate', 0) * 100
                cache_size_percent = (cache_stats.get('cache_size', 0) / cache_stats.get('max_cache_size', 1)) * 100
                
                visualizer.display_markdown(
                    f"# Promptcache-statistik\n\n"
                    f"- **Cache-storlek:** {cache_stats.get('cache_size', 0)}/{cache_stats.get('max_cache_size', 0)} ({cache_size_percent:.1f}%)\n"
                    f"- **Träffar:** {cache_stats.get('hits', 0)}\n"
                    f"- **Missar:** {cache_stats.get('misses', 0)}\n"
                    f"- **Träfffrekvens:** {hit_rate_percent:.1f}%\n"
                    f"- **Totala förfrågningar:** {cache_stats.get('total_requests', 0)}\n"
                )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Fel vid visualisering av cachestatistik: {str(e)}")
    
    def export_statistics(self, file_path: Union[str, Path] = None) -> None:
        """
        Exporterar statistik om promptsamlingen till en fil.
        
        Args:
            file_path: Sökväg till filen att exportera till. Om None, skapas en fil i storage_dir.
        """
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.storage_dir / f"prompt_statistics_{timestamp}.json"
        else:
            file_path = Path(file_path)
        
        # Samla statistik
        stats = {
            "timestamp": datetime.now().isoformat(),
            "total_prompts": len(self.prompts),
            "tag_stats": {},
            "type_stats": {},
            "prompts": {},
            "cache_stats": self.get_cache_stats() if self.use_cache else {"enabled": False}
        }
        
        # Samla taggstatistik
        for tag, prompt_names in self.by_tag.items():
            success_rates = [self.prompts[name].success_rate for name in prompt_names if name in self.prompts]
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
            
            latencies = [self.prompts[name].average_latency_ms for name in prompt_names if name in self.prompts]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            usage_counts = [self.prompts[name].usage_count for name in prompt_names if name in self.prompts]
            total_usage = sum(usage_counts)
            
            stats["tag_stats"][tag] = {
                "count": len(prompt_names),
                "avg_success_rate": avg_success_rate,
                "avg_latency_ms": avg_latency,
                "total_usage": total_usage
            }
        
        # Samla typstatistik
        for prompt_type, prompt_names in self.by_type.items():
            stats["type_stats"][prompt_type] = len(prompt_names)
        
        # Samla promptinformation
        for name, prompt in self.prompts.items():
            stats["prompts"][name] = {
                "type": self._get_prompt_type(prompt),
                "tags": prompt.tags,
                "version": prompt.version,
                "success_rate": prompt.success_rate,
                "avg_latency_ms": prompt.average_latency_ms,
                "usage_count": prompt.usage_count,
                "creation_time": prompt.creation_time.isoformat(),
                "last_modified": prompt.last_modified.isoformat()
            }
        
        # Spara till fil
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            if self.logger:
                self.logger.info(f"Exporterade promptstatistik till {file_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid export av promptstatistik: {str(e)}")

    def export_to_markdown(self, file_path: Union[str, Path] = None) -> None:
        """
        Exporterar översikt över promptsamlingen till en Markdown-fil.
        
        Args:
            file_path: Sökväg till filen att exportera till. Om None, skapas en fil i storage_dir.
        """
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.storage_dir / f"prompt_overview_{timestamp}.md"
        else:
            file_path = Path(file_path)
        
        # Skapa Markdown-innehåll
        md_lines = [
            "# Promptsamling - Översikt",
            "",
            f"Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Totalt antal promptmallar: **{len(self.prompts)}**",
            ""
        ]
        
        # Lägg till taggstatistik
        md_lines.extend([
            "## Taggar",
            "",
            "| Tagg | Antal | Framgångsfrekvens | Genomsnittlig svarstid |",
            "|------|-------|-------------------|-----------------------|"
        ])
        
        for tag, prompt_names in sorted(self.by_tag.items(), key=lambda x: len(x[1]), reverse=True):
            success_rates = [self.prompts[name].success_rate for name in prompt_names if name in self.prompts]
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
            
            latencies = [self.prompts[name].average_latency_ms for name in prompt_names if name in self.prompts]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            md_lines.append(f"| {tag} | {len(prompt_names)} | {avg_success_rate:.2f} | {avg_latency:.0f} ms |")
        
        # Lägg till typstatistik
        md_lines.extend([
            "",
            "## Prompttyper",
            "",
            "| Typ | Antal |",
            "|-----|-------|"
        ])
        
        for prompt_type, prompt_names in sorted(self.by_type.items(), key=lambda x: len(x[1]), reverse=True):
            md_lines.append(f"| {prompt_type} | {len(prompt_names)} |")
        
        # Lägg till de bästa promptarna
        md_lines.extend([
            "",
            "## Bästa promptar (baserat på framgångsfrekvens)",
            "",
            "| Namn | Taggar | Framgångsfrekvens | Svarstid | Användning |",
            "|------|--------|-------------------|----------|------------|"
        ])
        
        for prompt in sorted(self.prompts.values(), key=lambda p: p.success_rate, reverse=True)[:10]:
            tags_str = ", ".join(prompt.tags)
            md_lines.append(f"| {prompt.name} | {tags_str} | {prompt.success_rate:.2f} | {prompt.average_latency_ms:.0f} ms | {prompt.usage_count} |")
        
        # Lägg till de mest använda promptarna
        md_lines.extend([
            "",
            "## Mest använda promptar",
            "",
            "| Namn | Taggar | Framgångsfrekvens | Svarstid | Användning |",
            "|------|--------|-------------------|----------|------------|"
        ])
        
        for prompt in sorted(self.prompts.values(), key=lambda p: p.usage_count, reverse=True)[:10]:
            if prompt.usage_count > 0:
                tags_str = ", ".join(prompt.tags)
                md_lines.append(f"| {prompt.name} | {tags_str} | {prompt.success_rate:.2f} | {prompt.average_latency_ms:.0f} ms | {prompt.usage_count} |")
        
        # Lägg till cachestatistik
        if self.use_cache:
            cache_stats = self.get_cache_stats()
            hit_rate_percent = cache_stats.get('hit_rate', 0) * 100
            
            md_lines.extend([
                "",
                "## Cache-statistik",
                "",
                f"- **Cache aktiverad:** Ja",
                f"- **Cache-storlek:** {cache_stats.get('cache_size', 0)}/{cache_stats.get('max_cache_size', 0)}",
                f"- **Träffar:** {cache_stats.get('hits', 0)}",
                f"- **Missar:** {cache_stats.get('misses', 0)}",
                f"- **Träfffrekvens:** {hit_rate_percent:.1f}%",
                f"- **Totala förfrågningar:** {cache_stats.get('total_requests', 0)}"
            ])
        else:
            md_lines.extend([
                "",
                "## Cache-statistik",
                "",
                "- **Cache aktiverad:** Nej"
            ])
        
        # Spara till fil
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(md_lines))
            
            if self.logger:
                self.logger.info(f"Exporterade promptöversikt till {file_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fel vid export av promptöversikt: {str(e)}")

    def get_similar_prompts(self, name: str, max_count: int = 5) -> List[Dict[str, Any]]:
        """
        Hittar promptmallar som liknar den angivna prompten.
        
        Args:
            name: Namnet på promptmallen att jämföra med
            max_count: Maximalt antal liknande promptar att returnera
            
        Returns:
            List[Dict[str, Any]]: Lista med information om liknande promptmallar
        """
        if name not in self.prompts:
            if self.logger:
                self.logger.warning(f"Kunde inte hitta liknande promptar: {name} hittades inte")
            return []
        
        base_prompt = self.prompts[name]
        base_tags = set(base_prompt.tags)
        base_type = self._get_prompt_type(base_prompt)
        
        # Beräkna likhet för alla andra promptmallar
        similarities = []
        
        for other_name, other_prompt in self.prompts.items():
            if other_name == name:
                continue
            
            # Beräkna tag-likhet (Jaccard-index)
            other_tags = set(other_prompt.tags)
            tag_similarity = len(base_tags.intersection(other_tags)) / len(base_tags.union(other_tags)) if base_tags or other_tags else 0
            
            # Typlikhet (1.0 om samma typ, 0.5 om liknande typ, 0.0 annars)
            other_type = self._get_prompt_type(other_prompt)
            type_similarity = 1.0 if other_type == base_type else 0.5 if base_type in other_type or other_type in base_type else 0.0
            
            # Viktad totallikhet
            total_similarity = (tag_similarity * 0.7) + (type_similarity * 0.3)
            
            similarities.append({
                "name": other_name,
                "similarity": total_similarity,
                "tag_similarity": tag_similarity,
                "type_similarity": type_similarity,
                "prompt": other_prompt
            })
        
        # Sortera efter likhet (högst först) och begränsa antalet
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        top_similar = similarities[:max_count]
        
        # Konvertera till resultatformat
        result = []
        for similar in top_similar:
            prompt = similar["prompt"]
            result.append({
                "name": prompt.name,
                "similarity": similar["similarity"],
                "tags": prompt.tags,
                "type": self._get_prompt_type(prompt),
                "success_rate": prompt.success_rate,
                "usage_count": prompt.usage_count
            })
        
        return result







