#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ExtractionPrompt.py - Specialiserad klass för informationsextraktionspromptar

Denna modul innehåller klassen ExtractionPrompt, som är en specialiserad prompt
för att extrahera strukturerad information från text.

Egenskaper:
- JSON-schema för den förväntade extraktionen
- Förbättrade instruktioner baserat på schemastruktur
- Felförebyggande tips
- Konfidenspoäng för extraktioner
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .PromptTemplate import PromptTemplate


class ExtractionPrompt(PromptTemplate):
    """
    Specialiserad promptmall för extraktion av strukturerad information från text.
    
    Stödjer:
    - JSON-schema för den förväntade extraktionen
    - Förbättrade instruktioner baserat på schemastruktur
    - Felförebyggande tips
    - Konfidenspoäng för extraktioner
    """
    
    def __init__(self, template: str, schema: Dict[str, Any], name: str = None, 
                 description: str = None, version: str = "1.0", tags: List[str] = None,
                 extraction_type: str = "general", improved_instructions: str = None,
                 error_prevention: str = None):
        """
        Initierar extraktionsprompten.
        
        Args:
            template: Mall med platshållare
            schema: JSON-schema för den förväntade extraktionen
            name: Namn på promptmallen
            description: Beskrivning av promptmallen
            version: Versionsstring
            tags: Lista med taggar för kategorisering
            extraction_type: Typ av extraktion (general, compatibility, technical, combined, etc.)
            improved_instructions: Förbättrade instruktioner för prompten
            error_prevention: Felförebyggande tips för prompten
        """
        tags = tags or []
        if "extraction" not in tags:
            tags.append("extraction")
        if extraction_type and extraction_type not in tags:
            tags.append(extraction_type)
            
        super().__init__(template, name, description, version, tags)
        self.schema = schema
        self.extraction_type = extraction_type
        self.required_fields = self._extract_required_fields(schema)
        self.improved_instructions = improved_instructions
        self.error_prevention = error_prevention
    
    def _extract_required_fields(self, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extraherar obligatoriska fält från schemat för validering.
        
        Args:
            schema: JSON-schema att analysera
            
        Returns:
            Dict[str, List[str]]: Mappning av objekttyper till obligatoriska fält
        """
        required_fields = {}
        
        # Hantera produktinformation
        if "product" in schema:
            required_fields["product"] = ["title"]
        
        # Hantera kompatibilitetsschema
        if "relations" in schema:
            required_fields["relation"] = ["relation_type", "related_product", "context"]
            required_fields["related_product"] = ["name"]
        
        # Hantera tekniskt schema
        if "specifications" in schema:
            required_fields["specification"] = ["category", "name", "raw_value"]
        
        # Hantera datatabeller
        if "data_tables" in schema:
            required_fields["data_table"] = ["title", "rows"]
            required_fields["table_row"] = ["property", "value"]
        
        # Hantera FAQ-schema
        if "question_type" in schema or "compatible_products" in schema:
            required_fields["faq"] = ["question_type", "reference_product"]
            required_fields["compatible_product"] = ["product_name"]
        
        return required_fields
    
    def with_improved_instructions(self) -> 'ExtractionPrompt':
        """
        Förbättrar instruktionerna i prompten baserat på schemat.
        
        Returns:
            ExtractionPrompt: Ny promptmall med förbättrade instruktioner
        """
        if not self.improved_instructions:
            # Skapa grundläggande förbättrade instruktioner
            improved_instructions = [
                "VIKTIGT: Du MÅSTE följa dessa instruktioner exakt:",
                "1. Analysera texten noggrant innan du svarar",
                "2. Returnera ENDAST JSON i det begärda formatet utan någon extra text",
                "3. Inkludera endast information som faktiskt nämns i texten"
            ]
            
            # Lägg till schemaspecifika instruktioner
            if "product" in self.schema:
                improved_instructions.extend([
                    "4. För produktidentifiering, leta efter exakta artikel- och EAN-nummer",
                    "5. Utelämna fält som inte uttryckligen nämns i texten (t.ex. ange inte EAN om det inte finns)"
                ])
            
            if "relations" in self.schema:
                improved_instructions.extend([
                    "4. För kompatibilitetsrelationer, var mycket specifik med relationstypen",
                    "5. 'context' fältet ska innehålla den exakta meningen eller stycket där relationen nämndes",
                    "6. I 'related_product', inkludera artikelnummer när de anges",
                    "7. Försök identifiera båda sidor av relationen (vad som passar till vad)"
                ])
            
            if "specifications" in self.schema:
                improved_instructions.extend([
                    "4. För tekniska specifikationer, kategorisera korrekt (dimensioner, elektriska egenskaper, etc.)",
                    "5. Separera värde och enhet i 'raw_value' och 'unit' fälten när möjligt",
                    "6. Standardisera enheter när möjligt (mm, cm, kg, V, etc.)",
                    "7. Inkludera eventuella gränsvärden eller intervall i 'raw_value'"
                ])
            
            if "data_tables" in self.schema:
                improved_instructions.extend([
                    "4. För datatabeller, behåll exakt samma struktur och innehåll som i originalet",
                    "5. Varje rad i tabellen ska innehålla både 'property' och 'value'",
                    "6. Se till att extrahera hela tabellen, inte bara delar av den"
                ])
            
            if "compatible_products" in self.schema:
                improved_instructions.extend([
                    "4. För kompatibla produkter, inkludera hela produktnamnet och eventuella artikelnummer",
                    "5. Vid artikelnummer, ange både leverantör och nummer när båda finns",
                    "6. Inkludera endast produkter som uttryckligen anges som kompatibla",
                    "7. Var försiktig med att inte extrapolera kompatibilitet som inte uttryckligen anges"
                ])
            
            # Om detta är en kombinerad extraktion
            if self.extraction_type == "combined":
                improved_instructions.extend([
                    "8. Utelämna helt sektioner där ingen relevant information hittas (exempelvis ingen tom 'relations': [] om inga relationer finns)",
                    "9. För produktidentifiering, hitta titel, artikelnummer, EAN och eventuella andra identifierare",
                    "10. Se till att korrekt strukturera 'related_product' som ett objekt med 'name', 'article_number' och 'ean'"
                ])
            
            improved_instructions_text = "\n".join(improved_instructions)
        else:
            improved_instructions_text = self.improved_instructions
        
        # Hitta lämpligt ställe att infoga instruktionerna (före JSON-exempel)
        json_start = self.template.find("```json")
        
        if json_start > 0:
            # Hitta en lämplig plats innan JSON-exemplet
            svar_pos = self.template.find("Svar ENDAST i detta JSON-format")
            if svar_pos > 0 and svar_pos < json_start:
                improved_template = self.template.replace(
                    "Svar ENDAST i detta JSON-format",
                    f"{improved_instructions_text}\n\nSvar ENDAST i detta JSON-format"
                )
            else:
                # Lägg till före JSON-exemplet
                improved_template = (
                    self.template[:json_start] + 
                    f"{improved_instructions_text}\n\n" + 
                    self.template[json_start:]
                )
        else:
            # Lägg till i slutet av instruktionerna
            improved_template = self.template + f"\n\n{improved_instructions_text}"
        
        # Skapa en ny promptmall med förbättrade instruktioner
        return ExtractionPrompt(
            template=improved_template,
            schema=self.schema,
            name=f"{self.name}_improved",
            description=f"{self.description} (med förbättrade instruktioner)",
            version=f"{self.version}+impr",
            tags=self.tags + ["improved_instructions"],
            extraction_type=self.extraction_type,
            improved_instructions=improved_instructions_text,
            error_prevention=self.error_prevention
        )
    
    def with_error_prevention(self) -> 'ExtractionPrompt':
        """
        Lägger till instruktioner för att förebygga vanliga fel.
        
        Returns:
            ExtractionPrompt: Ny promptmall med felförebyggande instruktioner
        """
        if not self.error_prevention:
            # Skapa grundläggande felförebyggande tips
            error_prevention = "\n\nVANLIGA FEL ATT UNDVIKA:\n" + \
                "- Returnera inte text utanför JSON-objektet\n" + \
                "- Trunkera inte svaret eller använd '...' inuti JSON\n" + \
                "- Inkludera alla obligatoriska fält i varje objekt\n" + \
                "- Använd dubbla citattecken för JSON-nycklar och strängvärden\n" + \
                "- Kontrollera att JSON-strukturen är korrekt med korrekt nästlade objekt\n"
            
            # Lägg till extraktionsspecifika tips
            if "product" in self.schema:
                error_prevention += "- Ange inte EAN eller artikelnummer om de inte uttryckligen nämns i texten\n" + \
                    "- Extrahera inte produktinformation från rubriker om det inte är tydligt att det är produkttiteln\n"
            
            if "relations" in self.schema:
                error_prevention += "- Lämna inte tomma 'relation_type' eller 'related_product' fält\n" + \
                    "- Undvik att använda vaga relationstyper som 'relaterad' eller 'kopplad'\n" + \
                    "- Säkerställ att 'context' innehåller meningsfull text där relationen nämns\n"
            
            if "specifications" in self.schema:
                error_prevention += "- Undvik att blanda värde och enhet i 'value' fältet (använd 'raw_value' och 'unit')\n" + \
                    "- Välj specifika kategorier istället för 'annan' eller 'övrigt' när möjligt\n" + \
                    "- Standardisera enheter konsekvent genom hela svaret\n"
            
            if "data_tables" in self.schema:
                error_prevention += "- Extrahera tabeller korrekt rad för rad utan att blanda fälten\n" + \
                    "- Säkerställ att 'property' och 'value' korrekt representerar tabellens innehåll\n"
            
            if "compatible_products" in self.schema:
                error_prevention += "- Undvik duplicerade produkter i 'compatible_products' listan\n" + \
                    "- Inkludera komplett produktinformation inklusive artikelnummer när tillgängligt\n" + \
                    "- Lägg endast i produkter som uttryckligen anges som kompatibla\n"
            
            # Om detta är en kombinerad extraktion
            if self.extraction_type == "combined":
                error_prevention += "- Inkludera INTE tomma sektioner - om data saknas, utelämna hela sektionen\n" + \
                    "- Balansera mellan fullständighet och exakthet, extrahera bara faktiskt förekommande information\n" + \
                    "- Vid nästlade objekt, se till att de följer korrekt struktur (t.ex. 'related_product' som objekt)\n"
        else:
            error_prevention = self.error_prevention
        
        # Skapa en ny promptmall med felförebyggande tips
        improved_template = self.template + error_prevention
        
        return ExtractionPrompt(
            template=improved_template,
            schema=self.schema,
            name=f"{self.name}_error_prevention",
            description=f"{self.description} (med felförebyggande tips)",
            version=f"{self.version}+err",
            tags=self.tags + ["error_prevention"],
            extraction_type=self.extraction_type,
            improved_instructions=self.improved_instructions,
            error_prevention=error_prevention
        )


    def with_examples(self, examples: List[Dict[str, str]]) -> 'ExtractionPrompt':
        """
        Lägger till exempel för few-shot learning.
        
        Args:
            examples: Lista med exempel (input/output-par)
            
        Returns:
            ExtractionPrompt: Ny promptmall med exempel
        """
        examples_text = ""
        
        for i, example in enumerate(examples):
            examples_text += f"\n\nEXEMPEL {i+1}:\n\n"
            examples_text += "INPUT:\n"
            examples_text += f"```\n{example.get('input', '')}\n```\n\n"
            examples_text += "OUTPUT:\n"
            examples_text += f"```\n{example.get('output', '')}\n```"
        
        # Hitta lämpligt ställe att infoga exemplen (innan texten som ska analyseras)
        text_marker = "Här är produktdokumentationen:"
        
        if text_marker in self.template:
            parts = self.template.split(text_marker)
            new_template = parts[0] + "\nHär är några exempel på hur du ska formatera ditt svar:" + examples_text + "\n\n" + text_marker + parts[1]
        else:
            # Lägg till i slutet av inledningen
            paragraphs = self.template.split("\n\n")
            introduction_end = min(5, len(paragraphs))
            
            new_template = "\n\n".join(paragraphs[:introduction_end]) + \
                "\n\nHär är några exempel på hur du ska formatera ditt svar:" + examples_text + \
                "\n\n" + "\n\n".join(paragraphs[introduction_end:])
        
        # Skapa en ny promptmall med exempel
        return ExtractionPrompt(
            template=new_template,
            schema=self.schema,
            name=f"{self.name}_with_examples",
            description=f"{self.description} (med {len(examples)} exempel)",
            version=f"{self.version}+ex{len(examples)}",
            tags=self.tags + ["with_examples"],
            extraction_type=self.extraction_type,
            improved_instructions=self.improved_instructions,
            error_prevention=self.error_prevention
        )
    
    def for_model(self, model_name: str) -> 'ExtractionPrompt':
        """
        Anpassar prompten för en specifik modell.
        
        Args:
            model_name: Namn på modellen att anpassa för
            
        Returns:
            ExtractionPrompt: Ny promptmall anpassad för modellen
        """
        model_specific_instruction = ""
        model_lower = model_name.lower()
        
        # Lägg till modellspecifika instruktioner
        if "llama" in model_lower:
            model_specific_instruction = (
                "\n\nDu är en LLaMA-baserad AI-assistant. "
                "För att få bästa resultat, analysera texten steg för steg och var mycket noggrann "
                "med att följa JSON-formatet exakt. Var särskilt uppmärksam på att inte utelämna några obligatoriska fält."
            )
        elif any(name in model_lower for name in ["gpt", "chatgpt", "codex"]):
            model_specific_instruction = (
                "\n\nDu är en GPT-baserad AI-assistant. "
                "Använd din förmåga att strukturera information genom att först identifiera alla relevanta delar "
                "i texten, och sedan organisera dem i det begärda JSON-formatet."
            )
        elif "claude" in model_lower:
            model_specific_instruction = (
                "\n\nDu är Claude, en hjälpsam assistent. "
                "När du analyserar texten, var särskilt uppmärksam på detaljer och nyanser. "
                "Strukturera informationen tydligt och fullständigt i det begärda JSON-formatet."
            )
        elif "mistral" in model_lower:
            model_specific_instruction = (
                "\n\nDu är en Mistral-baserad AI-assistent. "
                "Använd din förmåga att förstå kontext och struktur för att extrahera information "
                "på ett strukturerat sätt. Var särskilt noggrann med JSON-formatering."
            )
        elif "gemini" in model_lower:
            model_specific_instruction = (
                "\n\nDu är en Gemini-baserad AI-assistent. "
                "Använd din multimodala förståelse för att extrahera information strukturerat "
                "och noggrant formatera JSON-svaret enligt instruktionerna."
            )
        else:
            model_specific_instruction = (
                f"\n\nDu använder modellen {model_name}. "
                "Arbeta systematiskt genom att först identifiera all relevant information "
                "och sedan strukturera den enligt det begärda JSON-formatet."
            )
        
        # Hitta lämpligt ställe att infoga instruktionen (i början)
        introduction_end = self.template.find("\n\n")
        if introduction_end > 0:
            new_template = self.template[:introduction_end] + model_specific_instruction + self.template[introduction_end:]
        else:
            new_template = model_specific_instruction + "\n\n" + self.template
        
        # Skapa en ny promptmall anpassad för modellen
        return ExtractionPrompt(
            template=new_template,
            schema=self.schema,
            name=f"{self.name}_for_{model_name.replace('-', '_')}",
            description=f"{self.description} (optimerad för {model_name})",
            version=f"{self.version}+{model_name.split('-')[0]}",
            tags=self.tags + [f"for_{model_name.replace('-', '_').lower()}", "model_specific"],
            extraction_type=self.extraction_type,
            improved_instructions=self.improved_instructions,
            error_prevention=self.error_prevention
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterar extraktionsprompten till en ordbok för serialisering.
        
        Returns:
            Dict[str, Any]: Extraktionsprompten som ordbok
        """
        data = super().to_dict()
        data.update({
            "schema": self.schema,
            "extraction_type": self.extraction_type,
            "improved_instructions": self.improved_instructions,
            "error_prevention": self.error_prevention
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionPrompt':
        """
        Skapar en extraktionsprompt från en ordbok.
        
        Args:
            data: Ordbok med promptdata
            
        Returns:
            ExtractionPrompt: Den skapade extraktionsprompten
        """
        # Extrahera schema och andra specialattribut
        schema = data.pop("schema", {})
        extraction_type = data.pop("extraction_type", "general")
        improved_instructions = data.pop("improved_instructions", None)
        error_prevention = data.pop("error_prevention", None)
        
        # Skapa extraktionsprompt
        prompt = cls(
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


