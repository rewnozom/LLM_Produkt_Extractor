#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PromptLoader.py - Klass för att ladda promptmallar från YAML-filer

Denna modul innehåller klassen PromptLoader, som hanterar laddning av olika
typer av promptmallar från YAML-filer och katalogstrukturer.

Funktioner:
- Ladda enskilda promptmallar från YAML-filer
- Ladda alla promptmallar från en katalog
- Skapa specialiserade promptmallar baserat på en basprompt
"""

import yaml
import os
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .PromptTemplate import PromptTemplate
from .ExtractionPrompt import ExtractionPrompt
from .ValidationPrompt import ValidationPrompt
from .CorrectionPrompt import CorrectionPrompt


class PromptLoader:
    """
    Klass för att ladda promptmallar från YAML-filer.
    
    Hanterar inläsning av promptmallar från filer och konstruktion
    av rätt promptobjekt baserat på fil-metadata.
    """
    
    @staticmethod
    def load_prompt_from_file(file_path: Union[str, Path], logger: Optional[logging.Logger] = None) -> PromptTemplate:
        """
        Laddar en promptmall från en YAML-fil.
        
        Args:
            file_path: Sökväg till YAML-filen
            logger: Logger för att logga meddelanden (valfritt)
            
        Returns:
            PromptTemplate: Den laddade promptmallen
            
        Raises:
            FileNotFoundError: Om filen inte hittas
            ValueError: Om filen har ogiltigt format
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            error_msg = f"Promptmallsfilen {file_path} hittades inte"
            if logger:
                logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if logger:
                logger.debug(f"Laddade YAML-data från {file_path}")
            
            # Identifiera prompttyp baserat på tags och innehåll
            if "extraction" in data.get("tags", []):
                # Extraktionsprompt
                schema = data.get("schema", {})
                extraction_type = data.get("extraction_type", "general")
                improved_instructions = data.get("improved_instructions")
                error_prevention = data.get("error_prevention")
                
                prompt = ExtractionPrompt(
                    template=data["template"],
                    schema=schema,
                    name=data.get("name"),
                    description=data.get("description"),
                    version=data.get("version", "1.0"),
                    tags=data.get("tags", []),
                    extraction_type=extraction_type,
                    improved_instructions=improved_instructions,
                    error_prevention=error_prevention
                )
                
                if logger:
                    logger.debug(f"Skapade ExtractionPrompt: {prompt.name} (typ: {extraction_type})")
                
                return prompt
                
            elif "validation" in data.get("tags", []):
                # Valideringsprompt
                validation_rules = data.get("validation_rules", [])
                
                prompt = ValidationPrompt(
                    template=data["template"],
                    validation_rules=validation_rules,
                    name=data.get("name"),
                    description=data.get("description"),
                    version=data.get("version", "1.0"),
                    tags=data.get("tags", [])
                )
                
                if logger:
                    logger.debug(f"Skapade ValidationPrompt: {prompt.name}")
                
                return prompt
                
            elif "correction" in data.get("tags", []):
                # Korrigeringsprompt
                error_types = data.get("error_types", {})
                
                prompt = CorrectionPrompt(
                    template=data["template"],
                    error_types=error_types,
                    name=data.get("name"),
                    description=data.get("description"),
                    version=data.get("version", "1.0"),
                    tags=data.get("tags", [])
                )
                
                if logger:
                    logger.debug(f"Skapade CorrectionPrompt: {prompt.name}")
                
                return prompt
                
            else:
                # Generell promptmall
                prompt = PromptTemplate(
                    template=data["template"],
                    name=data.get("name"),
                    description=data.get("description"),
                    version=data.get("version", "1.0"),
                    tags=data.get("tags", [])
                )
                
                if logger:
                    logger.debug(f"Skapade PromptTemplate: {prompt.name}")
                
                return prompt
                
        except yaml.YAMLError as e:
            error_msg = f"Filen {file_path} innehåller ogiltig YAML: {str(e)}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)
        except KeyError as e:
            error_msg = f"Filen {file_path} saknar nödvändigt fält: {e}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Oväntat fel vid laddning av promptmall från {file_path}: {str(e)}"
            if logger:
                logger.error(error_msg)
            raise
    
    @staticmethod
    def load_prompts_from_directory(
        directory: Union[str, Path], 
        recursive: bool = True, 
        logger: Optional[logging.Logger] = None
    ) -> Dict[str, PromptTemplate]:
        """
        Laddar alla promptmallar från en katalog.
        
        Args:
            directory: Katalog att ladda från
            recursive: Om underkataloger ska inkluderas
            logger: Logger för att logga meddelanden (valfritt)
            
        Returns:
            Dict[str, PromptTemplate]: Ordbok med laddade promptmallar
        """
        directory = Path(directory)
        
        if not directory.exists():
            if logger:
                logger.warning(f"Katalogen {directory} existerar inte")
            return {}
        
        prompts = {}
        pattern = "**/*.yaml" if recursive else "*.yaml"
        
        if logger:
            logger.info(f"Söker efter promptmallar i {directory} {'(rekursivt)' if recursive else ''}")
        
        for file_path in directory.glob(pattern):
            try:
                if logger:
                    logger.debug(f"Försöker ladda prompt från {file_path}")
                
                prompt = PromptLoader.load_prompt_from_file(file_path, logger)
                prompts[prompt.name] = prompt
                
                if logger:
                    logger.info(f"Laddade prompt: {prompt.name} från {file_path}")
            except Exception as e:
                if logger:
                    logger.error(f"Kunde inte ladda {file_path}: {str(e)}")
                else:
                    print(f"Kunde inte ladda {file_path}: {str(e)}")
        
        if logger:
            logger.info(f"Laddade totalt {len(prompts)} promptmallar från {directory}")
        
        return prompts
    
    @staticmethod
    def create_specialized_prompt_from_yaml(
        file_path: Union[str, Path], 
        logger: Optional[logging.Logger] = None
    ) -> Optional[PromptTemplate]:
        """
        Skapar en specialiserad prompt från en YAML-fil.
        
        Args:
            file_path: Sökväg till YAML-filen
            logger: Logger för att logga meddelanden (valfritt)
            
        Returns:
            Optional[PromptTemplate]: Den skapade promptmallen eller None om det inte gick
        """
        try:
            file_path = Path(file_path)
            
            # Ladda YAML-filen
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Kontrollera om det är en specialiserad prompt
            if "based_on" in data and "focus_area" in data:
                # Ladda basprompten
                base_name = data["based_on"]
                base_prompt = None
                
                # Sök efter basprompten i samma katalog
                dir_path = file_path.parent
                for yaml_file in dir_path.glob("*.yaml"):
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                        
                        if yaml_data.get("name") == base_name:
                            base_prompt = PromptLoader.load_prompt_from_file(yaml_file, logger)
                            break
                    except Exception:
                        continue
                
                if base_prompt is None:
                    error_msg = f"Kunde inte hitta basprompt {base_name} för {file_path}"
                    if logger:
                        logger.error(error_msg)
                    return None
                
                # Skapa specialiserad prompt
                focus_area = data["focus_area"]
                additional_instructions = data.get("additional_instructions", [])
                
                if logger:
                    logger.info(f"Skapar specialiserad prompt baserad på {base_name} med fokus på {focus_area}")
                
                # Skapa en specialiserad prompt
                focus_instructions = f"\n\nFOKUSERA SÄRSKILT PÅ: {focus_area}\n"
                
                if additional_instructions:
                    focus_instructions += "Ytterligare specialinstruktioner:\n"
                    for i, instruction in enumerate(additional_instructions):
                        focus_instructions += f"{i+1}. {instruction}\n"
                
                # Hitta rätt position att lägga till instruktionerna (före JSON-exemplet)
                template = base_prompt.template
                json_start = template.find("```json")
                if json_start > 0:
                    new_template = template[:json_start] + focus_instructions + template[json_start:]
                else:
                    # Lägg till i början om JSON-exemplet inte hittas
                    new_template = focus_instructions + template
                
                # Skapa rätt typ av prompt baserat på basmallen
                if isinstance(base_prompt, ExtractionPrompt):
                    specialized_prompt = ExtractionPrompt(
                        template=new_template,
                        schema=base_prompt.schema,
                        name=data.get("name", f"{base_prompt.name}_{focus_area.lower().replace(' ', '_')}"),
                        description=data.get("description", f"{base_prompt.description} (specialiserad för {focus_area})"),
                        version=data.get("version", f"{base_prompt.version}+spec"),
                        tags=data.get("tags", base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')]),
                        extraction_type=data.get("extraction_type", base_prompt.extraction_type),
                        improved_instructions=base_prompt.improved_instructions,
                        error_prevention=base_prompt.error_prevention
                    )
                elif isinstance(base_prompt, ValidationPrompt):
                    specialized_prompt = ValidationPrompt(
                        template=new_template,
                        validation_rules=base_prompt.validation_rules,
                        name=data.get("name", f"{base_prompt.name}_{focus_area.lower().replace(' ', '_')}"),
                        description=data.get("description", f"{base_prompt.description} (specialiserad för {focus_area})"),
                        version=data.get("version", f"{base_prompt.version}+spec"),
                        tags=data.get("tags", base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')])
                    )
                elif isinstance(base_prompt, CorrectionPrompt):
                    specialized_prompt = CorrectionPrompt(
                        template=new_template,
                        error_types=base_prompt.error_types,
                        name=data.get("name", f"{base_prompt.name}_{focus_area.lower().replace(' ', '_')}"),
                        description=data.get("description", f"{base_prompt.description} (specialiserad för {focus_area})"),
                        version=data.get("version", f"{base_prompt.version}+spec"),
                        tags=data.get("tags", base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')])
                    )
                else:
                    specialized_prompt = PromptTemplate(
                        template=new_template,
                        name=data.get("name", f"{base_prompt.name}_{focus_area.lower().replace(' ', '_')}"),
                        description=data.get("description", f"{base_prompt.description} (specialiserad för {focus_area})"),
                        version=data.get("version", f"{base_prompt.version}+spec"),
                        tags=data.get("tags", base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')])
                    )
                
                if logger:
                    logger.info(f"Skapade specialiserad prompt: {specialized_prompt.name}")
                
                return specialized_prompt
            else:
                # Vanlig promptladding
                if logger:
                    logger.debug(f"Filen {file_path} är inte en specialiserad prompt, laddar som vanlig prompt")
                return PromptLoader.load_prompt_from_file(file_path, logger)
        
        except Exception as e:
            error_msg = f"Kunde inte skapa specialiserad prompt från {file_path}: {str(e)}"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            return None
    
    @staticmethod
    def load_default_prompts(logger: Optional[logging.Logger] = None) -> Dict[str, PromptTemplate]:
        """
        Laddar fördefinierade promptmallar som är inbyggda i systemet.
        
        Args:
            logger: Logger för att logga meddelanden (valfritt)
            
        Returns:
            Dict[str, PromptTemplate]: Ordbok med fördefinierade promptmallar
        """
        import os
        from pathlib import Path
        
        # Hitta sökvägen till denna modul för att lokalisera YAML-filerna relativt till den
        module_path = Path(__file__).parent
        
        default_prompts = {}
        
        # Filsökvägar till default templates
        template_files = {
            "default_combined_template": module_path / "default.yaml",
            "combined_correction_template": module_path / "corrections" / "error.yaml",
            "combined_validation_template": module_path / "validation" / "validation.yaml"
        }
        
        # Ladda templates från YAML-filer
        for name, file_path in template_files.items():
            if file_path.exists():
                try:
                    prompt = PromptLoader.load_prompt_from_file(file_path, logger)
                    default_prompts[name] = prompt
                    
                    if logger:
                        logger.debug(f"Laddade fördefinierad promptmall {name} från {file_path}")
                except Exception as e:
                    if logger:
                        logger.error(f"Kunde inte ladda fördefinierad promptmall {name}: {str(e)}")
        
        if logger:
            logger.info(f"Laddade {len(default_prompts)} fördefinierade promptmallar")
        
        return default_prompts
    
    @staticmethod
    def save_prompt_to_file(
        prompt: PromptTemplate, 
        directory: Union[str, Path], 
        override: bool = False,
        logger: Optional[logging.Logger] = None
    ) -> Optional[Path]:
        """
        Sparar en promptmall till fil.
        
        Args:
            prompt: Promptmallen att spara
            directory: Katalog att spara till
            override: Om befintliga filer ska skrivas över
            logger: Logger för att logga meddelanden (valfritt)
            
        Returns:
            Optional[Path]: Sökväg till den sparade filen, eller None om det inte gick
        """
        try:
            directory = Path(directory)
            directory.mkdir(exist_ok=True, parents=True)
            
            # Skapa filnamn baserat på namn och version
            safe_name = prompt.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_name}_v{prompt.version.replace('.', '_')}.yaml"
            file_path = directory / filename
            
            # Kontrollera om filen redan finns
            if file_path.exists() and not override:
                if logger:
                    logger.warning(f"Filen {file_path} finns redan och override=False")
                return None
            
            # Spara till YAML
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml_content = prompt.to_yaml()
                f.write(yaml_content)
            
            if logger:
                logger.info(f"Sparade promptmall {prompt.name} till {file_path}")
            
            return file_path
        
        except Exception as e:
            error_msg = f"Kunde inte spara promptmall {prompt.name}: {str(e)}"
            if logger:
                logger.error(error_msg)
            return None