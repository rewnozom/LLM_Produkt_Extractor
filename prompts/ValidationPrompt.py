#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ValidationPrompt.py - Specialiserad klass för validering av LLM-svar

Denna modul innehåller klassen ValidationPrompt, som är en specialiserad prompt
för att validera strukturerade svar från LLM.

Egenskaper:
- Lista med valideringsregler
- Schemaspecifik validering
- Detaljerad felrapportering
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .PromptTemplate import PromptTemplate


class ValidationPrompt(PromptTemplate):
    """
    Specialiserad promptmall för validering av LLM-svar.
    
    Används för att verifiera att extraherad information är korrekt,
    fullständig och följer det förväntade formatet.
    """
    
    def __init__(self, template: str, validation_rules: List[str], name: str = None, 
                 description: str = None, version: str = "1.0", tags: List[str] = None):
        """
        Initierar valideringsprompten.
        
        Args:
            template: Mall med platshållare
            validation_rules: Lista med valideringsregler
            name: Namn på promptmallen
            description: Beskrivning av promptmallen
            version: Versionsstring
            tags: Lista med taggar för kategorisering
        """
        tags = tags or []
        if "validation" not in tags:
            tags.append("validation")
            
        super().__init__(template, name, description, version, tags)
        self.validation_rules = validation_rules
    
    def format(self, **kwargs) -> str:
        """
        Fyller mallen med värden och lägger till valideringsregler.
        
        Args:
            **kwargs: Nyckelord att ersätta i mallen
            
        Returns:
            str: Den formaterade prompten
        """
        # Lägg till valideringsregler i kwargs om de inte redan finns
        if 'validation_rules' not in kwargs:
            rules_text = "\n".join([f"- {rule}" for rule in self.validation_rules])
            kwargs['validation_rules'] = rules_text
        
        # Använd baspromptens format-metod
        return super().format(**kwargs)
    
    def with_specific_schema(self, schema: Dict[str, Any]) -> 'ValidationPrompt':
        """
        Anpassar valideringsprompten för ett specifikt schema.
        
        Args:
            schema: JSON-schema att validera mot
            
        Returns:
            ValidationPrompt: Ny promptmall med schemaspecifika regler
        """
        # Generera schemaspecifika regler
        schema_rules = []
        
        # Hantera produktinformation
        if "product" in schema:
            schema_rules.extend([
                "Produktinformation måste ha fältet 'title'",
                "Om 'article_number' eller 'ean' finns ska de vara korrekt formaterade",
                "Om 'additional_identifiers' finns ska det vara en lista med 'type' och 'value' fält"
            ])
        
        # Hantera kompatibilitetsschema
        if "relations" in schema:
            schema_rules.extend([
                "Varje relation måste ha fälten 'relation_type', 'related_product' och 'context'",
                "Relationstypen ska vara specifik och tydlig (t.ex. 'passar till', 'ersätter', 'kräver')",
                "Relaterad produkt ska ha fältet 'name' och gärna 'article_number' och 'ean' när tillgängligt",
                "Kontexten ska innehålla texten där relationen nämns"
            ])
        
        # Hantera tekniskt schema
        if "specifications" in schema:
            schema_rules.extend([
                "Varje specifikation måste ha fälten 'category', 'name', 'raw_value'",
                "Kategorin ska vara specifik och beskrivande",
                "Värdet ska vara korrekt formaterat med enhet när lämpligt",
                "Numeriska värden ska vara strukturerade med 'value' och 'unit' fält när möjligt"
            ])
        
        # Hantera datatabeller
        if "data_tables" in schema:
            schema_rules.extend([
                "Varje datatabell måste ha fälten 'title' och 'rows'",
                "Tabell-rader måste innehålla 'property' och 'value' för varje rad",
                "Tabeller ska korrekt representera den strukturerade datan från originaltexten"
            ])
        
        # Hantera FAQ-schema
        if "compatible_products" in schema:
            schema_rules.extend([
                "Svaret måste innehålla 'question_type' och 'reference_product'",
                "Varje kompatibel produkt måste ha 'product_name' och gärna 'article_numbers'",
                "Produktnamnet ska vara fullständigt och exakt"
            ])
        
        # Hantera tomma sektioner för kombinerade schemata
        if len(schema.keys()) > 1:
            schema_rules.extend([
                "Tomma sektioner ska utelämnas helt, inte inkluderas som tomma objekt eller listor",
                "Endast sektioner med faktisk extraherad data ska inkluderas i resultatet"
            ])
        
        # Kombinera befintliga och nya regler
        combined_rules = self.validation_rules + schema_rules
        
        # Skapa en ny promptmall med de kombinerade reglerna
        return ValidationPrompt(
            template=self.template,
            validation_rules=combined_rules,
            name=f"{self.name}_schema_specific",
            description=f"{self.description} (med schemaspecifika regler)",
            version=f"{self.version}+schema",
            tags=self.tags + ["schema_specific"]
        )
    
    def with_error_detection(self) -> 'ValidationPrompt':
        """
        Lägger till förbättrad feldetektering i valideringsprompten.
        
        Returns:
            ValidationPrompt: Ny promptmall med förbättrad feldetektering
        """
        # Lägg till extra valideringsregler för feldetektering
        error_detection_rules = [
            "Kontrollera om värden har rimlig storleksordning",
            "Identifiera saknade relationer eller specifikationer som nämns i texten men saknas i resultatet",
            "Verifiera att enheter är korrekt standardiserade (mm, cm, kg, etc.)",
            "Kontrollera om relationstyperna är konsistenta genom hela dokumentet",
            "Upptäck om det finns konflikterande eller motstridiga informationsbitar",
            "Identifiera potentiella formaterings- eller tolkningsfel i numeriska värden"
        ]
        
        # Kombinera befintliga och nya regler
        combined_rules = self.validation_rules + error_detection_rules
        
        # Modifiera mallen för att inkludera feldetektering
        detection_section = """
För varje identifierat fel, ange:
1. Exakt var felet finns (fält, objekt, index)
2. Felbeskrivning (vad är fel)
3. Förväntad korrekt form
4. Svårighetsgrad (kritisk/allvarlig/mindre)

Var särskilt uppmärksam på:
- Avvikelser från det förväntade schemat
- Bristande eller felaktig tolkning av originaldata
- Saknad information som uppenbart finns i källtexten
- Inkonsistenta format eller värdetyper
"""
        
        # Hitta lämpligt ställe att infoga instruktionerna
        result_format_pos = self.template.find("Returnera ditt resultat i följande format:")
        
        if result_format_pos > 0:
            new_template = (
                self.template[:result_format_pos] + 
                detection_section + 
                "\n\n" + 
                self.template[result_format_pos:]
            )
        else:
            new_template = self.template + "\n\n" + detection_section
        
        # Skapa en ny promptmall med förbättrad feldetektering
        return ValidationPrompt(
            template=new_template,
            validation_rules=combined_rules,
            name=f"{self.name}_enhanced_detection",
            description=f"{self.description} (med förbättrad feldetektering)",
            version=f"{self.version}+detect",
            tags=self.tags + ["enhanced_detection"]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterar valideringsprompten till en ordbok för serialisering.
        
        Returns:
            Dict[str, Any]: Valideringsprompten som ordbok
        """
        data = super().to_dict()
        data["validation_rules"] = self.validation_rules
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationPrompt':
        """
        Skapar en valideringsprompt från en ordbok.
        
        Args:
            data: Ordbok med promptdata
            
        Returns:
            ValidationPrompt: Den skapade valideringsprompten
        """
        # Extrahera valideringsregler
        validation_rules = data.pop("validation_rules", [])
        
        # Skapa valideringsprompt
        prompt = cls(
            template=data["template"],
            validation_rules=validation_rules,
            name=data.get("name"),
            description=data.get("description"),
            version=data.get("version", "1.0"),
            tags=data.get("tags", [])
        )
        
        # Ställ in ytterligare attribut om de finns
        if "creation_time" in data:
            prompt.creation_time = datetime.fromisoformat(data["creation_time"])
        
        if "last_modified" in data:
            prompt.last_modified = datetime.fromisoformat(data["last_modified"])
        
        if "usage_count" in data:
            prompt.usage_count = data["usage_count"]
        
        if "success_rate" in data:
            prompt.success_rate = data["success_rate"]
        
        if "average_latency_ms" in data:
            prompt.average_latency_ms = data["average_latency_ms"]
        
        return prompt