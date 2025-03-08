
        
        
        
        #!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ./Processor/ProductProcessor.py


"""
ProductProcessor för LLM-baserad Produktinformationsextraktor

Denna modul innehåller:
1. ProductProcessor - Huvudklass för bearbetning av produktdokumentation
2. ProductResult - Klass för att representera resultatet av bearbetningen
3. ValidationResult - Klass för validering av extraherad information
4. ResultMerger - Hjälpklass för att sammanfoga resultat från olika källor

Modulen hanterar den fullständiga bearbetningsprocessen för produkter, från inläsning
av filer till strukturering av data och validering av resultaten.
"""

import os
import re
import json
import time
import hashlib
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import logging
import traceback

from client import LLMClient, ChunkManager
from prompts import (
    PromptTemplate
)

class ExtractionStatus(Enum):
    """Status för extraktionsprocessen"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class ValidationResult:
    """Resultat av validering"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Lägger till ett fel"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str) -> None:
        """Lägger till en varning"""
        self.warnings.append(warning)
    
    def __bool__(self) -> bool:
        """Bool-konvertering för enkel kontroll"""
        return self.valid


@dataclass
class ProductResult:
    """Resultat av produktbearbetning"""
    product_id: str
    status: ExtractionStatus = ExtractionStatus.NOT_STARTED
    compatibility: Dict[str, Any] = field(default_factory=dict)
    technical: Dict[str, Any] = field(default_factory=dict)
    faq_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialisera metadata"""
        if not self.metadata:
            self.metadata = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processing_time_ms": 0,
                "file_size": 0,
                "chunked": False,
                "chunks_count": 0
            }
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Uppdaterar metadata"""
        self.metadata[key] = value
        self.metadata["updated_at"] = datetime.now().isoformat()
    
    def add_error(self, error: str) -> None:
        """Lägger till ett fel"""
        self.errors.append(error)
        if self.status not in [ExtractionStatus.FAILED, ExtractionStatus.PARTIALLY_COMPLETED]:
            self.status = ExtractionStatus.FAILED
    
    def add_warning(self, warning: str) -> None:
        """Lägger till en varning"""
        self.warnings.append(warning)
    
    def get_compatibility_count(self) -> int:
        """Returnerar antal kompatibilitetsrelationer"""
        return len(self.compatibility.get("relations", []))
    
    def get_technical_count(self) -> int:
        """Returnerar antal tekniska specifikationer"""
        return len(self.technical.get("specifications", []))
    
    def to_dict(self) -> Dict[str, Any]:
        """Konverterar till ordbok för serialisering"""
        return {
            "product_id": self.product_id,
            "status": self.status.value,
            "compatibility": self.compatibility,
            "technical": self.technical,
            "faq_data": self.faq_data,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class ResultMerger:
    """Hjälpklass för att sammanfoga resultat från olika källor"""
    
    @staticmethod
    def merge_compatibility_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sammanfogar kompatibilitetsresultat från flera källor
        
        Args:
            results: Lista med kompatibilitetsresultat
            
        Returns:
            Dict[str, Any]: Sammanfogat resultat
        """
        if not results:
            return {"relations": []}
        
        # Samla alla relationer
        all_relations = []
        for result in results:
            if isinstance(result, dict) and "relations" in result:
                all_relations.extend(result["relations"])
        
        # Skapa en nyckel för varje relation för att identifiera dubbletter
        unique_relations = {}
        for relation in all_relations:
            if not isinstance(relation, dict):
                continue
            
            # Skapa en nyckel baserad på relation_type och related_product
            key_parts = [
                relation.get("relation_type", "").lower(),
                relation.get("related_product", "").lower()
            ]
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Om relationen inte finns eller har högre förtroende, lägg till den
            if key not in unique_relations or relation.get("confidence", 0) > unique_relations[key].get("confidence", 0):
                unique_relations[key] = relation
        
        return {"relations": list(unique_relations.values())}
    
    @staticmethod
    def merge_technical_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sammanfogar tekniska resultat från flera källor
        
        Args:
            results: Lista med tekniska resultat
            
        Returns:
            Dict[str, Any]: Sammanfogat resultat
        """
        if not results:
            return {"specifications": []}
        
        # Samla alla specifikationer
        all_specs = []
        for result in results:
            if isinstance(result, dict) and "specifications" in result:
                all_specs.extend(result["specifications"])
        
        # Skapa en nyckel för varje specifikation för att identifiera dubbletter
        unique_specs = {}
        for spec in all_specs:
            if not isinstance(spec, dict):
                continue
            
            # Skapa en nyckel baserad på kategori och namn
            key_parts = [
                spec.get("category", "").lower(),
                spec.get("name", "").lower()
            ]
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Om specifikationen inte finns eller har högre förtroende, lägg till den
            if key not in unique_specs or spec.get("confidence", 0) > unique_specs[key].get("confidence", 0):
                unique_specs[key] = spec
        
        return {"specifications": list(unique_specs.values())}
    
    @staticmethod
    def merge_faq_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sammanfogar FAQ-resultat från flera källor
        
        Args:
            results: Lista med FAQ-resultat
            
        Returns:
            Dict[str, Any]: Sammanfogat resultat
        """
        if not results:
            return {}
        
        # Börja med det första resultatet som bas
        merged = results[0].copy() if results else {}
        
        # Om det inte finns någon kompatibel produkt, samla från alla resultat
        if "compatible_products" in merged:
            all_products = merged.get("compatible_products", [])
            
            # Lägg till produkter från andra resultat
            for result in results[1:]:
                if isinstance(result, dict) and "compatible_products" in result:
                    all_products.extend(result["compatible_products"])
            
            # Ta bort dubbletter baserat på produktnamn
            unique_products = {}
            for product in all_products:
                if not isinstance(product, dict):
                    continue
                
                product_name = product.get("product_name", "").lower()
                
                if product_name and (product_name not in unique_products or 
                                    product.get("confidence", 0) > unique_products[product_name].get("confidence", 0)):
                    unique_products[product_name] = product
            
            merged["compatible_products"] = list(unique_products.values())
        
        # Sammanfoga additional_info från alla resultat om det finns
        additional_info = set()
        for result in results:
            if isinstance(result, dict) and "additional_info" in result:
                info = result["additional_info"].strip()
                if info:
                    additional_info.add(info)
        
        if additional_info:
            merged["additional_info"] = ". ".join(additional_info)
        
        return merged


class ProductProcessor:
    """
    Huvudklass för bearbetning av produktdokumentation
    """
    
    def __init__(
        self, config: Dict[str, Any], llm_client: LLMClient, logger: logging.Logger, 
        visualizer=None, prompt_manager=None
    ):
        """
        Initierar produktprocessorn
        
        Args:
            config: Konfiguration för processorn
            llm_client: LLM-klient för att kommunicera med LLM-tjänsten
            logger: Logger för att logga meddelanden
            visualizer: Visualiserare för att visa information i terminalen
            prompt_manager: Prompthanterare för att hantera promptmallar
        """
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.visualizer = visualizer
        self.prompt_manager = prompt_manager
        
        # Registrera prompthanteraren med LLM-klienten om tillgänglig
        if self.prompt_manager and hasattr(self.llm_client, 'set_prompt_manager'):
            self.llm_client.set_prompt_manager(self.prompt_manager)
        
        # Skapa chunk-hanterare för stora filer
        self.chunk_manager = ChunkManager(config.get("extraction", {}), logger)
        
        # Konfigurera extraktionsinställningar
        self.extract_compatibility = config.get("extraction", {}).get("compatibility", {}).get("enabled", True)
        self.extract_technical = config.get("extraction", {}).get("technical", {}).get("enabled", True)
        self.extract_faq = config.get("extraction", {}).get("faq", {}).get("enabled", False)
        
        # Tröskelvärden för förtroende
        self.compatibility_threshold = config.get("extraction", {}).get("compatibility", {}).get("threshold", 0.7)
        self.technical_threshold = config.get("extraction", {}).get("technical", {}).get("threshold", 0.7)
        
        # Initialisera resultatspårning
        self.processed_count = 0
        self.success_count = 0
        self.partial_count = 0
        self.fail_count = 0
        
        # Cacheriktory för att spara temporära resultat
        self.cache_dir = Path(config.get("general", {}).get("cache_dir", "./cache"))
        self.cache_dir.mkdir(exist_ok=True, parents=True)
    
    def register_prompt_callbacks(self, 
                                 update_stats_callback: Callable[[str, bool, int], None],
                                 get_prompt_callback: Callable[[List[str], float], Optional[PromptTemplate]]) -> None:
        """
        Registrerar callbacks för prompthantering
        
        Args:
            update_stats_callback: Callback för att uppdatera användningsstatistik
            get_prompt_callback: Callback för att hämta bästa promptmall
        """
        self.update_prompt_stats = update_stats_callback
        self.get_best_prompt = get_prompt_callback
        
        self.logger.debug("Registrerade promptcallbacks i produktprocessorn")
    
    def process_product(self, product_id: str, file_path: Union[str, Path]) -> ProductResult:
        """
        Bearbetar en produkts dokumentation
        
        Args:
            product_id: ID för produkten
            file_path: Sökväg till filen med produktdokumentation
            
        Returns:
            ProductResult: Resultatet av bearbetningen
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        # Logga start av bearbetning
        self.logger.workflow(f"Börjar bearbeta produkt {product_id}")
        if self.visualizer:
            self.visualizer.display_markdown(f"# Bearbetar produkt: {product_id}\nFil: {file_path}")
        
        # Skapa resultatobjekt
        result = ProductResult(product_id=product_id, status=ExtractionStatus.IN_PROGRESS)
        
        # Kontrollera om filen finns
        if not file_path.exists():
            error_msg = f"Filen {file_path} existerar inte"
            self.logger.error(error_msg)
            result.add_error(error_msg)
            result.status = ExtractionStatus.FAILED
            return result
        
        # Uppdatera metadata
        result.update_metadata("file_path", str(file_path))
        result.update_metadata("file_size", file_path.stat().st_size)
        
        try:
            # Läs filinnehåll
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Kontrollera om innehållet behöver chunkas
            chunked = self.chunk_manager.should_chunk(content)
            result.update_metadata("chunked", chunked)
            
            if chunked:
                chunks = self.chunk_manager.chunk_text(content)
                result.update_metadata("chunks_count", len(chunks))
                self.logger.workflow(f"Delade upp innehållet i {len(chunks)} bitar")
                
                # Bearbeta varje bit
                compatibility_results = []
                technical_results = []
                faq_results = []
                
                for i, chunk in enumerate(chunks):
                    self.logger.workflow(f"Bearbetar bit {i+1}/{len(chunks)}")
                    
                    # Extrahera information från denna bit
                    chunk_result = self._process_content(chunk, product_id, f"chunk_{i+1}")
                    
                    if self.extract_compatibility and chunk_result.compatibility:
                        compatibility_results.append(chunk_result.compatibility)
                    
                    if self.extract_technical and chunk_result.technical:
                        technical_results.append(chunk_result.technical)
                    
                    if self.extract_faq and chunk_result.faq_data:
                        faq_results.append(chunk_result.faq_data)
                    
                    # Överför fel och varningar från chunken
                    for error in chunk_result.errors:
                        result.add_error(f"Bit {i+1}: {error}")
                    
                    for warning in chunk_result.warnings:
                        result.add_warning(f"Bit {i+1}: {warning}")
                
                # Sammanfoga resultaten
                if compatibility_results:
                    result.compatibility = ResultMerger.merge_compatibility_results(compatibility_results)
                
                if technical_results:
                    result.technical = ResultMerger.merge_technical_results(technical_results)
                
                if faq_results:
                    result.faq_data = ResultMerger.merge_faq_results(faq_results)
            else:
                # Bearbeta hela innehållet på en gång
                chunk_result = self._process_content(content, product_id)
                
                if self.extract_compatibility:
                    result.compatibility = chunk_result.compatibility
                
                if self.extract_technical:
                    result.technical = chunk_result.technical
                
                if self.extract_faq:
                    result.faq_data = chunk_result.faq_data
                
                # Överför fel och varningar
                result.errors.extend(chunk_result.errors)
                result.warnings.extend(chunk_result.warnings)
            
            # Uppdatera status baserat på resultat
            if result.errors:
                if (result.get_compatibility_count() > 0 or result.get_technical_count() > 0 or result.faq_data):
                    result.status = ExtractionStatus.PARTIALLY_COMPLETED
                    self.partial_count += 1
                else:
                    result.status = ExtractionStatus.FAILED
                    self.fail_count += 1
            else:
                result.status = ExtractionStatus.COMPLETED
                self.success_count += 1
            
        except Exception as e:
            # Hantera oväntade fel
            error_msg = f"Oväntat fel vid bearbetning: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result.add_error(error_msg)
            result.status = ExtractionStatus.FAILED
            self.fail_count += 1
        
        # Uppdatera bearbetningstid
        processing_time = int((time.time() - start_time) * 1000)  # ms
        result.update_metadata("processing_time_ms", processing_time)
        
        # Uppdatera räknare
        self.processed_count += 1
        
        # Logga slutförande
        self.logger.workflow(
            f"Slutförde bearbetning av produkt {product_id} med status {result.status.value} "
            f"på {processing_time} ms"
        )
        
        # Visa resultatsammanfattning
        if self.visualizer:
            self._display_result_summary(result)
        
        return result
    
    def _process_content(self, content: str, product_id: str, chunk_id: str = None) -> ProductResult:
        """
        Bearbetar innehåll för att extrahera information
        
        Args:
            content: Textinnehåll att bearbeta
            product_id: ID för produkten
            chunk_id: ID för chunken (om chunked)
            
        Returns:
            ProductResult: Resultatet av bearbetningen
        """
        result = ProductResult(
            product_id=product_id, 
            status=ExtractionStatus.IN_PROGRESS,
            metadata={"chunk_id": chunk_id} if chunk_id else {}
        )
        
        # Extrahera kompatibilitetsinformation om aktiverat
        if self.extract_compatibility:
            try:
                self.logger.workflow(f"Extraherar kompatibilitetsinformation{' för ' + chunk_id if chunk_id else ''}")
                
                # Använd prompthanteraren om tillgänglig för att välja bästa prompt
                compatibility_prompt = None
                if hasattr(self, 'get_best_prompt') and self.get_best_prompt:
                    compatibility_prompt = self.get_best_prompt(["compatibility", "extraction"], self.compatibility_threshold)
                
                # Extrahera kompatibilitetsinformation
                compatibility = self.llm_client.extract_compatibility_info(content, prompt_template=compatibility_prompt)
                
                # Uppdatera promptstatistik om tillgänglig
                if compatibility and hasattr(self, 'update_prompt_stats') and self.update_prompt_stats and compatibility_prompt:
                    success = "relations" in compatibility and len(compatibility.get("relations", [])) > 0
                    self.update_prompt_stats(compatibility_prompt.name, success, self.llm_client.last_latency_ms)
                
                if compatibility:
                    # Filtrera bort lågt förtroende
                    if "relations" in compatibility:
                        filtered_relations = []
                        for relation in compatibility["relations"]:
                            if relation.get("confidence", 0) >= self.compatibility_threshold:
                                filtered_relations.append(relation)
                            else:
                                self.logger.warning(
                                    f"Filtrerade bort kompatibilitetsrelation med lågt förtroende: "
                                    f"{relation.get('relation_type')} - {relation.get('related_product')}"
                                )
                        
                        compatibility["relations"] = filtered_relations
                    
                    result.compatibility = compatibility
                    self.logger.extraction(
                        f"Extraherade {len(compatibility.get('relations', []))} kompatibilitetsrelationer"
                    )
            except Exception as e:
                error_msg = f"Fel vid extrahering av kompatibilitetsinformation: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Extrahera tekniska specifikationer om aktiverat
        if self.extract_technical:
            try:
                self.logger.workflow(f"Extraherar tekniska specifikationer{' för ' + chunk_id if chunk_id else ''}")
                
                # Använd prompthanteraren om tillgänglig för att välja bästa prompt
                technical_prompt = None
                if hasattr(self, 'get_best_prompt') and self.get_best_prompt:
                    technical_prompt = self.get_best_prompt(["technical", "extraction"], self.technical_threshold)
                
                # Extrahera tekniska specifikationer
                technical = self.llm_client.extract_technical_specs(content, prompt_template=technical_prompt)
                
                # Uppdatera promptstatistik om tillgänglig
                if technical and hasattr(self, 'update_prompt_stats') and self.update_prompt_stats and technical_prompt:
                    success = "specifications" in technical and len(technical.get("specifications", [])) > 0
                    self.update_prompt_stats(technical_prompt.name, success, self.llm_client.last_latency_ms)
                
                if technical:
                    # Filtrera bort lågt förtroende
                    if "specifications" in technical:
                        filtered_specs = []
                        for spec in technical["specifications"]:
                            if spec.get("confidence", 0) >= self.technical_threshold:
                                filtered_specs.append(spec)
                            else:
                                self.logger.warning(
                                    f"Filtrerade bort teknisk specifikation med lågt förtroende: "
                                    f"{spec.get('category')} - {spec.get('name')}"
                                )
                        
                        technical["specifications"] = filtered_specs
                    
                    result.technical = technical
                    self.logger.extraction(
                        f"Extraherade {len(technical.get('specifications', []))} tekniska specifikationer"
                    )
            except Exception as e:
                error_msg = f"Fel vid extrahering av tekniska specifikationer: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Extrahera FAQ-data om aktiverat
        if self.extract_faq:
            try:
                self.logger.workflow(f"Extraherar FAQ-data{' för ' + chunk_id if chunk_id else ''}")
                
                # Använd prompthanteraren om tillgänglig för att välja bästa prompt
                faq_prompt = None
                if hasattr(self, 'get_best_prompt') and self.get_best_prompt:
                    faq_prompt = self.get_best_prompt(["faq", "extraction"], 0.7)
                
                # Använd produktkompatibilitet FAQ-prompten
                from .. import product_compatibility_faq_template
                prompt_template = faq_prompt or product_compatibility_faq_template
                
                # Skapa prompt och hämta svar
                formatted_prompt = prompt_template.format(text=content)
                response = self.llm_client.get_completion(formatted_prompt)
                
                # Uppdatera promptstatistik om tillgänglig
                if response.successful and hasattr(self, 'update_prompt_stats') and self.update_prompt_stats and faq_prompt:
                    self.update_prompt_stats(faq_prompt.name, response.successful, self.llm_client.last_latency_ms)
                
                if response.successful:
                    # Tolka svaret som JSON
                    try:
                        from .. import ResponseParser
                        parser = ResponseParser(self.logger)
                        faq_data = parser.extract_json(response.text)
                        
                        if faq_data:
                            result.faq_data = faq_data
                            self.logger.extraction(
                                f"Extraherade FAQ-data med {len(faq_data.get('compatible_products', []))} "
                                f"kompatibla produkter"
                            )
                    except Exception as e:
                        error_msg = f"Fel vid tolkning av FAQ-svar: {str(e)}"
                        self.logger.error(error_msg)
                        result.add_error(error_msg)
            except Exception as e:
                error_msg = f"Fel vid extrahering av FAQ-data: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        return result
    
    def validate_result(self, result: ProductResult) -> ValidationResult:
        """
        Validerar resultatet av bearbetningen
        
        Args:
            result: Resultatet att validera
            
        Returns:
            ValidationResult: Valideringsresultatet
        """
        validation = ValidationResult(valid=True)
        
        # Kontrollera grundläggande struktur
        if not result:
            validation.add_error("Resultat saknas")
            return validation
        
        # Validera kompatibilitetsinformation
        if self.extract_compatibility and result.compatibility:
            if "relations" not in result.compatibility:
                validation.add_error("Kompatibilitetsresultat saknar 'relations'-fältet")
            elif not isinstance(result.compatibility["relations"], list):
                validation.add_error("Kompatibilitetsrelationer är inte en lista")
            else:
                # Validera varje relation
                for i, relation in enumerate(result.compatibility["relations"]):
                    if not isinstance(relation, dict):
                        validation.add_error(f"Relation {i} är inte ett objekt")
                        continue
                    
                    # Kontrollera obligatoriska fält
                    for field in ["relation_type", "related_product", "context"]:
                        if field not in relation:
                            validation.add_error(f"Relation {i} saknar obligatoriskt fält '{field}'")
        
        # Validera tekniska specifikationer
        if self.extract_technical and result.technical:
            if "specifications" not in result.technical:
                validation.add_error("Tekniskt resultat saknar 'specifications'-fältet")
            elif not isinstance(result.technical["specifications"], list):
                validation.add_error("Tekniska specifikationer är inte en lista")
            else:
                # Validera varje specifikation
                for i, spec in enumerate(result.technical["specifications"]):
                    if not isinstance(spec, dict):
                        validation.add_error(f"Specifikation {i} är inte ett objekt")
                        continue
                    
                    # Kontrollera obligatoriska fält
                    for field in ["category", "name", "raw_value"]:
                        if field not in spec:
                            validation.add_error(f"Specifikation {i} saknar obligatoriskt fält '{field}'")
        
        # Validera FAQ-data
        if self.extract_faq and result.faq_data:
            if not isinstance(result.faq_data, dict):
                validation.add_error("FAQ-data är inte ett objekt")
            else:
                for field in ["question_type", "reference_product"]:
                    if field not in result.faq_data:
                        validation.add_error(f"FAQ-data saknar obligatoriskt fält '{field}'")
                
                if "compatible_products" in result.faq_data:
                    if not isinstance(result.faq_data["compatible_products"], list):
                        validation.add_error("Compatible_products är inte en lista")
        
        # Uppdatera resultatets status baserat på validering
        if validation.valid:
            result.status = ExtractionStatus.VALIDATED
        else:
            result.status = ExtractionStatus.VALIDATION_FAILED
            
            # Lägg till valideringsfel i resultatet
            for error in validation.errors:
                result.add_error(f"Valideringsfel: {error}")
            
            for warning in validation.warnings:
                result.add_warning(f"Valideringsvarning: {warning}")
        
        return validation
    
    def save_result(self, result: ProductResult, output_dir: Union[str, Path]) -> Tuple[bool, Path]:
        """
        Sparar resultatet till fil
        
        Args:
            result: Resultatet att spara
            output_dir: Katalog att spara i
            
        Returns:
            Tuple[bool, Path]: (framgång, filsökväg)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Skapa filnamn
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.product_id}_{timestamp}.json"
        file_path = output_dir / filename
        
        try:
            # Konvertera till ordbok och spara
            result_dict = result.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Sparade resultat för produkt {result.product_id} till {file_path}")
            return True, file_path
        except Exception as e:
            self.logger.error(f"Fel vid sparande av resultat för produkt {result.product_id}: {str(e)}")
            return False, None


    def save_structured_data(self, result: ProductResult, output_dir: Union[str, Path]) -> Dict[str, Path]:
        """
        Sparar strukturerad data i separata filer
        
        Args:
            result: Resultatet att spara
            output_dir: Katalog att spara i
            
        Returns:
            Dict[str, Path]: Sökvägar till sparade filer
        """
        base_dir = Path(output_dir)
        saved_files = {}
        
        # Skapa produkt-specifik katalog
        product_dir = base_dir / result.product_id
        product_dir.mkdir(exist_ok=True, parents=True)
        
        # Spara kompatibilitetsinformation
        if self.extract_compatibility and result.compatibility and result.compatibility.get("relations"):
            compat_path = product_dir / "compatibility.json"
            
            try:
                with open(compat_path, 'w', encoding='utf-8') as f:
                    json.dump(result.compatibility, f, ensure_ascii=False, indent=2)
                
                saved_files["compatibility"] = compat_path
                self.logger.info(f"Sparade kompatibilitetsinformation för {result.product_id} till {compat_path}")
            except Exception as e:
                self.logger.error(f"Fel vid sparande av kompatibilitetsinformation för {result.product_id}: {str(e)}")
        
        # Spara tekniska specifikationer
        if self.extract_technical and result.technical and result.technical.get("specifications"):
            tech_path = product_dir / "technical_specs.json"
            
            try:
                with open(tech_path, 'w', encoding='utf-8') as f:
                    json.dump(result.technical, f, ensure_ascii=False, indent=2)
                
                saved_files["technical"] = tech_path
                self.logger.info(f"Sparade tekniska specifikationer för {result.product_id} till {tech_path}")
            except Exception as e:
                self.logger.error(f"Fel vid sparande av tekniska specifikationer för {result.product_id}: {str(e)}")
        
        # Spara FAQ-data
        if self.extract_faq and result.faq_data:
            faq_path = product_dir / "faq_data.json"
            
            try:
                with open(faq_path, 'w', encoding='utf-8') as f:
                    json.dump(result.faq_data, f, ensure_ascii=False, indent=2)
                
                saved_files["faq"] = faq_path
                self.logger.info(f"Sparade FAQ-data för {result.product_id} till {faq_path}")
            except Exception as e:
                self.logger.error(f"Fel vid sparande av FAQ-data för {result.product_id}: {str(e)}")
        
        # Spara metadata
        metadata_path = product_dir / "metadata.json"
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                metadata = {
                    "product_id": result.product_id,
                    "status": result.status.value,
                    "created_at": result.metadata.get("created_at"),
                    "updated_at": result.metadata.get("updated_at"),
                    "processing_time_ms": result.metadata.get("processing_time_ms"),
                    "file_size": result.metadata.get("file_size"),
                    "chunked": result.metadata.get("chunked"),
                    "chunks_count": result.metadata.get("chunks_count"),
                    "compatibility_count": result.get_compatibility_count(),
                    "technical_count": result.get_technical_count(),
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings)
                }
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            saved_files["metadata"] = metadata_path
            self.logger.info(f"Sparade metadata för {result.product_id} till {metadata_path}")
        except Exception as e:
            self.logger.error(f"Fel vid sparande av metadata för {result.product_id}: {str(e)}")
        
        return saved_files
    
    def save_to_cache(self, result: ProductResult) -> bool:
        """
        Sparar resultatet till cachekatalogen
        
        Args:
            result: Resultatet att spara
            
        Returns:
            bool: True om lyckad, False annars
        """
        cache_file = self.cache_dir / f"{result.product_id}_cache.json"
        
        try:
            # Konvertera till ordbok och spara
            result_dict = result.to_dict()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"Sparade cache för produkt {result.product_id}")
            return True
        except Exception as e:
            self.logger.warning(f"Kunde inte spara cache för produkt {result.product_id}: {str(e)}")
            return False
    
    def load_from_cache(self, product_id: str) -> Optional[ProductResult]:
        """
        Laddar resultat från cachekatalogen
        
        Args:
            product_id: ID för produkten
            
        Returns:
            Optional[ProductResult]: Laddat resultat eller None om det inte finns
        """
        cache_file = self.cache_dir / f"{product_id}_cache.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                result_dict = json.load(f)
            
            # Skapa ProductResult från ordboken
            result = ProductResult(product_id=result_dict["product_id"])
            result.status = ExtractionStatus(result_dict["status"])
            result.compatibility = result_dict.get("compatibility", {})
            result.technical = result_dict.get("technical", {})
            result.faq_data = result_dict.get("faq_data", {})
            result.errors = result_dict.get("errors", [])
            result.warnings = result_dict.get("warnings", [])
            result.metadata = result_dict.get("metadata", {})
            
            self.logger.debug(f"Laddade cache för produkt {product_id}")
            return result
        except Exception as e:
            self.logger.warning(f"Kunde inte ladda cache för produkt {product_id}: {str(e)}")
            return None
    
    def generate_faq_answer(self, product_id: str, question: str, result: Optional[ProductResult] = None) -> str:
        """
        Genererar ett strukturerat FAQ-svar baserat på extraherad information
        
        Args:
            product_id: ID för produkten
            question: Frågan att besvara
            result: Tidigare extraherat resultat eller None
            
        Returns:
            str: Strukturerat svar på frågan
        """
        # Ladda resultat från cache om inte angivet
        if not result:
            result = self.load_from_cache(product_id)
            
            if not result:
                return f"Ingen information tillgänglig för produkt {product_id}."
        
        # Identifiera frågetyp
        question_lower = question.lower()
        
        # Frågor om vilka produkter som passar till en specifik produkt
        if any(pattern in question_lower for pattern in ["vilka", "vilken", "passa", "passar", "kompatibel"]):
            # Kontrollera om vi har FAQ-data
            if result.faq_data and "compatible_products" in result.faq_data:
                compatible_products = result.faq_data.get("compatible_products", [])
                
                if not compatible_products:
                    return f"Ingen kompatibilitetsinformation hittades för {product_id}."
                
                # Skapa ett snyggt formaterat Markdown-svar
                answer = f"# Kompatibla produkter för {product_id}\n\n"
                
                for product in compatible_products:
                    product_name = product.get("product_name", "")
                    article_numbers = product.get("article_numbers", [])
                    url = product.get("url", "")
                    
                    answer += f"## {product_name}\n\n"
                    
                    if article_numbers:
                        answer += "**Artikelnummer:**\n\n"
                        for article in article_numbers:
                            supplier = article.get("supplier", "")
                            number = article.get("number", "")
                            answer += f"- {supplier}: {number}\n"
                        answer += "\n"
                    
                    if url:
                        answer += f"**Länk:** [{url}]({url})\n\n"
                    
                    if "compatibility_context" in product:
                        answer += f"**Information:** {product.get('compatibility_context')}\n\n"
                
                if "additional_info" in result.faq_data:
                    answer += f"---\n\n**Ytterligare information:** {result.faq_data.get('additional_info')}\n"
                
                return answer
            
            # Alternativt, försök att bygga ett svar från kompatibilitetsrelationer
            elif result.compatibility and "relations" in result.compatibility:
                relations = result.compatibility.get("relations", [])
                
                if not relations:
                    return f"Ingen kompatibilitetsinformation hittades för {product_id}."
                
                # Skapa ett snyggt formaterat Markdown-svar
                answer = f"# Kompatibilitetsinformation för {product_id}\n\n"
                
                # Gruppera relationer efter typ
                relation_groups = {}
                for relation in relations:
                    relation_type = relation.get("relation_type", "Okänd")
                    if relation_type not in relation_groups:
                        relation_groups[relation_type] = []
                    relation_groups[relation_type].append(relation)
                
                # Skapa sektioner för varje relationstyp
                for relation_type, group_relations in relation_groups.items():
                    answer += f"## Produkter som {relation_type}\n\n"
                    
                    for relation in group_relations:
                        product = relation.get("related_product", "")
                        context = relation.get("context", "")
                        
                        answer += f"- **{product}**\n"
                        if context:
                            answer += f"  *{context}*\n\n"
                
                return answer
            
            else:
                return f"Ingen kompatibilitetsinformation hittades för {product_id}."
        
        # Frågor om tekniska specifikationer
        elif any(pattern in question_lower for pattern in ["specifikation", "teknisk", "mått", "vikt", "material"]):
            if result.technical and "specifications" in result.technical:
                specs = result.technical.get("specifications", [])
                
                if not specs:
                    return f"Inga tekniska specifikationer hittades för {product_id}."
                
                # Skapa ett snyggt formaterat Markdown-svar
                answer = f"# Tekniska specifikationer för {product_id}\n\n"
                
                # Gruppera specifikationer efter kategori
                category_groups = {}
                for spec in specs:
                    category = spec.get("category", "Okänd")
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(spec)
                
                # Skapa sektioner för varje kategori
                for category, category_specs in category_groups.items():
                    answer += f"## {category.capitalize()}\n\n"
                    
                    for spec in category_specs:
                        name = spec.get("name", "")
                        raw_value = spec.get("raw_value", "")
                        
                        answer += f"- **{name}:** {raw_value}\n"
                    
                    answer += "\n"
                
                return answer
            else:
                return f"Inga tekniska specifikationer hittades för {product_id}."
        
        # Generell information
        else:
            # Samla all information vi har
            answer = f"# Produktinformation för {product_id}\n\n"
            
            has_info = False
            
            # Lägg till kompatibilitetsinformation om tillgänglig
            if result.compatibility and "relations" in result.compatibility:
                relations = result.compatibility.get("relations", [])
                
                if relations:
                    has_info = True
                    answer += "## Kompatibilitetsinformation\n\n"
                    
                    for relation in relations[:5]:  # Begränsa till de första 5 för överblick
                        relation_type = relation.get("relation_type", "")
                        product = relation.get("related_product", "")
                        
                        answer += f"- {relation_type}: **{product}**\n"
                    
                    if len(relations) > 5:
                        answer += f"- ... samt {len(relations) - 5} fler kompatibilitetsrelationer\n"
                    
                    answer += "\n"
            
            # Lägg till tekniska specifikationer om tillgängliga
            if result.technical and "specifications" in result.technical:
                specs = result.technical.get("specifications", [])
                
                if specs:
                    has_info = True
                    answer += "## Tekniska specifikationer\n\n"
                    
                    for spec in specs[:5]:  # Begränsa till de första 5 för överblick
                        category = spec.get("category", "")
                        name = spec.get("name", "")
                        raw_value = spec.get("raw_value", "")
                        
                        answer += f"- {category} - {name}: **{raw_value}**\n"
                    
                    if len(specs) > 5:
                        answer += f"- ... samt {len(specs) - 5} fler specifikationer\n"
                    
                    answer += "\n"
            
            if not has_info:
                return f"Ingen detaljerad information hittades för {product_id}."
            
            return answer
    
    def _display_result_summary(self, result: ProductResult) -> None:
        """
        Visar en sammanfattning av resultatet i konsolen
        
        Args:
            result: Resultatet att visa
        """
        if not self.visualizer:
            return
        
        # Skapa tabelldata för kompatibilitetsrelationer
        if result.compatibility and "relations" in result.compatibility:
            relations = result.compatibility.get("relations", [])
            
            if relations:
                self.visualizer.display_markdown("## Extraherade kompatibilitetsrelationer")
                
                headers = ["Relationstyp", "Relaterad produkt", "Förtroende", "Kontext"]
                rows = []
                
                for relation in relations:
                    row = [
                        relation.get("relation_type", ""),
                        relation.get("related_product", ""),
                        f"{relation.get('confidence', 0):.2f}",
                        relation.get("context", "")[:50] + ("..." if len(relation.get("context", "")) > 50 else "")
                    ]
                    rows.append(row)
                
                self.visualizer.display_table(headers, rows, "Kompatibilitetsrelationer")
        
        # Skapa tabelldata för tekniska specifikationer
        if result.technical and "specifications" in result.technical:
            specs = result.technical.get("specifications", [])
            
            if specs:
                self.visualizer.display_markdown("## Extraherade tekniska specifikationer")
                
                headers = ["Kategori", "Namn", "Värde", "Enhet", "Förtroende"]
                rows = []
                
                for spec in specs:
                    row = [
                        spec.get("category", ""),
                        spec.get("name", ""),
                        spec.get("raw_value", ""),
                        spec.get("unit", ""),
                        f"{spec.get('confidence', 0):.2f}"
                    ]
                    rows.append(row)
                
                self.visualizer.display_table(headers, rows, "Tekniska specifikationer")
        
        # Visa fel och varningar
        if result.errors:
            self.visualizer.display_markdown("## Fel")
            for error in result.errors:
                self.visualizer.display_error(error)
        
        if result.warnings:
            self.visualizer.display_markdown("## Varningar")
            warning_text = "\n".join([f"- {warning}" for warning in result.warnings])
            self.visualizer.display_markdown(warning_text)
        
        # Visa sammanfattning
        self.visualizer.display_markdown("## Sammanfattning")
        summary = f"""
| Egenskap | Värde |
|----------|-------|
| Produktid | {result.product_id} |
| Status | {result.status.value} |
| Kompatibilitetsrelationer | {result.get_compatibility_count()} |
| Tekniska specifikationer | {result.get_technical_count()} |
| Fel | {len(result.errors)} |
| Varningar | {len(result.warnings)} |
| Bearbetningstid | {result.metadata.get('processing_time_ms', 0)} ms |
        """
        self.visualizer.display_markdown(summary)


















