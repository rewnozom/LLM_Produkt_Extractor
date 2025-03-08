#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
prompt_utils.py - Hjälpfunktioner för prompthantering

Denna modul innehåller hjälpfunktioner för att arbeta med promptmallar,
inklusive förbättring med exempel och specialisering av promptmallar.

Dessa funktioner kan användas separat från huvudklasserna för att
snabbt modifiera och anpassa promptmallar utan att direkt interagera
med prompthanteringsklasserna.
"""

from typing import Dict, List, Any, Optional, Union

from .PromptTemplate import PromptTemplate
from .ExtractionPrompt import ExtractionPrompt
from .ValidationPrompt import ValidationPrompt
from .CorrectionPrompt import CorrectionPrompt


def enhance_prompt_with_examples(prompt_template: PromptTemplate, examples: List[Dict[str, Any]]) -> PromptTemplate:
    """
    Förbättrar en promptmall med few-shot-exempel.
    
    Args:
        prompt_template: Mallprompt att förbättra
        examples: Lista med exempel (input/output-par)
        
    Returns:
        PromptTemplate: Förbättrad promptmall
    """
    # Skapa en formatterad text med alla exempel
    examples_text = ""
    
    for i, example in enumerate(examples):
        examples_text += f"\n\nEXEMPEL {i+1}:\n\n"
        examples_text += "INPUT:\n"
        examples_text += f"```\n{example.get('input', '')}\n```\n\n"
        examples_text += "OUTPUT:\n"
        examples_text += f"```\n{example.get('output', '')}\n```"
    
    # Lägg till exemplen i mallen
    if "{examples}" in prompt_template.template:
        return PromptTemplate(
            prompt_template.template.format(examples=examples_text),
            prompt_template.name + "_with_examples",
            prompt_template.description + " (med exempel)",
            prompt_template.version + "+ex",
            prompt_template.tags + ["with_examples"]
        )
    else:
        # Hitta rätt position att lägga till exemplen (före textinput)
        text_marker = "Här är produktdokumentationen:"
        if text_marker in prompt_template.template:
            parts = prompt_template.template.split(text_marker)
            new_template = parts[0] + "\nHär är några exempel på hur du ska formatera ditt svar:" + examples_text + "\n\n" + text_marker + parts[1]
            return PromptTemplate(
                new_template,
                prompt_template.name + "_with_examples",
                prompt_template.description + " (med exempel)",
                prompt_template.version + "+ex",
                prompt_template.tags + ["with_examples"]
            )
        else:
            # Lägg till exemplen i slutet av introduktionen
            lines = prompt_template.template.strip().split("\n\n")
            intro_end = min(10, len(lines) // 3)  # Uppskatta slutet på introduktionen
            
            new_template = "\n\n".join(lines[:intro_end]) + "\n\nHär är några exempel på hur du ska formatera ditt svar:" + examples_text + "\n\n" + "\n\n".join(lines[intro_end:])
            return PromptTemplate(
                new_template,
                prompt_template.name + "_with_examples",
                prompt_template.description + " (med exempel)",
                prompt_template.version + "+ex",
                prompt_template.tags + ["with_examples"]
            )


def create_specialized_prompt(base_prompt: PromptTemplate, focus_area: str, additional_instructions: List[str] = None) -> PromptTemplate:
    """
    Skapar en specialiserad prompt baserad på en basmall.
    
    Args:
        base_prompt: Basmallen att utgå från
        focus_area: Fokusområdet för specialiseringen
        additional_instructions: Ytterligare instruktioner att lägga till
        
    Returns:
        PromptTemplate: Specialiserad promptmall
    """
    # Skapa en kopia av basmallen
    template_text = base_prompt.template
    
    # Lägg till specialiseringsinstruktioner
    focus_instructions = f"\n\nFOKUSERA SÄRSKILT PÅ: {focus_area}\n"
    
    if additional_instructions:
        focus_instructions += "Ytterligare specialinstruktioner:\n"
        for i, instruction in enumerate(additional_instructions):
            focus_instructions += f"{i+1}. {instruction}\n"
    
    # Hitta rätt position att lägga till instruktionerna (före JSON-exemplet)
    json_start = template_text.find("```json")
    if json_start > 0:
        new_template = template_text[:json_start] + focus_instructions + template_text[json_start:]
    else:
        # Lägg till i början om JSON-exemplet inte hittas
        new_template = focus_instructions + template_text
    
    # Skapa rätt typ av prompt baserat på basmallen

    if isinstance(base_prompt, ExtractionPrompt):
        return ExtractionPrompt(
            template=new_template,
            schema=base_prompt.schema,
            name=base_prompt.name + f"_{focus_area.lower().replace(' ', '_')}",
            description=base_prompt.description + f" (specialiserad för {focus_area})",
            version=f"{base_prompt.version}+spec",
            tags=base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')],
            extraction_type=base_prompt.extraction_type,
            improved_instructions=base_prompt.improved_instructions,
            error_prevention=base_prompt.error_prevention
        )
    elif isinstance(base_prompt, ValidationPrompt):
        return ValidationPrompt(
            template=new_template,
            validation_rules=base_prompt.validation_rules,
            name=base_prompt.name + f"_{focus_area.lower().replace(' ', '_')}",
            description=base_prompt.description + f" (specialiserad för {focus_area})",
            version=f"{base_prompt.version}+spec",
            tags=base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')]
        )
    elif isinstance(base_prompt, CorrectionPrompt):
        return CorrectionPrompt(
            template=new_template,
            error_types=base_prompt.error_types,
            name=base_prompt.name + f"_{focus_area.lower().replace(' ', '_')}",
            description=base_prompt.description + f" (specialiserad för {focus_area})",
            version=f"{base_prompt.version}+spec",
            tags=base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')]
        )
    else:
        return PromptTemplate(
            template=new_template,
            name=base_prompt.name + f"_{focus_area.lower().replace(' ', '_')}",
            description=base_prompt.description + f" (specialiserad för {focus_area})",
            version=f"{base_prompt.version}+spec",
            tags=base_prompt.tags + ["specialized", focus_area.lower().replace(' ', '_')]
        )


def fix_json_format(json_text: str) -> str:
    """
    Försöker rätta till vanliga formatteringsfel i JSON-strängar.
    
    Args:
        json_text: JSON-text att korrigera
        
    Returns:
        str: Korrigerad JSON-text
    """
    import re
    import json
    
    # Rensa bort text före och efter JSON
    # Hitta första förekomsten av '{'
    start_idx = json_text.find('{')
    if start_idx == -1:
        # Ingen JSON-struktur hittades
        return json_text
    
    # Hitta sista förekomsten av '}'
    end_idx = json_text.rfind('}')
    if end_idx == -1 or end_idx < start_idx:
        # Ogiltig JSON-struktur
        return json_text
    
    # Extrahera JSON-delen
    json_part = json_text[start_idx:end_idx+1]
    
    # Fixa vanliga problem
    
    # 1. Fixa trailing commas (ogiltiga i JSON)
    json_part = re.sub(r',\s*}', '}', json_part)
    json_part = re.sub(r',\s*]', ']', json_part)
    
    # 2. Fixa saknade citattecken runt nycklar
    json_part = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', json_part)
    
    # 3. Fixa enkla citattecken
    single_quote_pattern = r"'(.*?)'"
    # Ersätt bara om det inte är inom ett värde med dubbla citattecken
    i = 0
    result = ""
    in_double_quotes = False
    while i < len(json_part):
        if json_part[i] == '"' and (i == 0 or json_part[i-1] != '\\'):
            in_double_quotes = not in_double_quotes
            result += json_part[i]
        elif json_part[i] == "'" and not in_double_quotes:
            result += '"'
        else:
            result += json_part[i]
        i += 1
    json_part = result
    
    # 4. Fixa ogiltig escape-sekvens
    json_part = json_part.replace('\\"', '\\\\"')
    
    # 5. Kontrollera att det är giltig JSON
    try:
        json.loads(json_part)
        return json_part
    except json.JSONDecodeError:
        # Om det fortfarande inte är giltig JSON, returnera originaltexten
        return json_text


def extract_schema_from_json(json_example: str) -> Dict[str, Any]:
    """
    Extraherar ett schema från ett JSON-exempel.
    
    Args:
        json_example: JSON-exempel som text
        
    Returns:
        Dict[str, Any]: Schema baserat på exemplet
    """
    import json
    
    try:
        # Försök tolka JSON-exemplet
        example_data = json.loads(json_example)
        
        # Skapa ett schema baserat på strukturen
        schema = {}
        
        for key, value in example_data.items():
            if isinstance(value, list):
                # Om det är en lista, representera det som en tom lista
                schema[key] = []
            elif isinstance(value, dict):
                # Om det är ett objekt, skapa ett schema rekursivt
                schema[key] = extract_schema_from_json(json.dumps(value))
            else:
                # För andra typer, använd None som platshållare
                schema[key] = None
        
        return schema
    except json.JSONDecodeError:
        # Om det inte är giltig JSON, returnera ett tomt schema
        return {}


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extraherar JSON från text genom att leta efter JSON-kodblock.
    
    Args:
        text: Text som kan innehålla JSON
        
    Returns:
        Optional[str]: Extraherad JSON eller None om ingen hittades
    """
    import re
    import json
    
    # Försök hitta JSON-kodblock först
    json_block_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})```"
    matches = re.findall(json_block_pattern, text)
    
    if matches:
        # Försök tolka varje matchning och returnera den första giltiga
        for match in matches:
            try:
                # Kontrollera att det är giltig JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                # Försök fixa formatteringsfel och kontrollera igen
                fixed_json = fix_json_format(match)
                try:
                    json.loads(fixed_json)
                    return fixed_json
                except json.JSONDecodeError:
                    continue
    
    # Om inga kodblock hittades, leta efter JSON direkt i texten
    # Hitta första förekomsten av '{'
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    # Hitta matchande '}'
    # Detta är en förenklad implementering och hanterar inte nästlade objekt perfekt
    brace_count = 0
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                # Vi har hittat slutet på JSON-objektet
                json_str = text[start_idx:i+1]
                
                try:
                    # Kontrollera att det är giltig JSON
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # Försök fixa formatteringsfel och kontrollera igen
                    fixed_json = fix_json_format(json_str)
                    try:
                        json.loads(fixed_json)
                        return fixed_json
                    except json.JSONDecodeError:
                        return None
    
    return None


def improve_prompt_based_on_feedback(prompt_template: PromptTemplate, feedback: str) -> PromptTemplate:
    """
    Förbättrar en promptmall baserat på textfeedback.
    
    Args:
        prompt_template: Promptmallen att förbättra
        feedback: Textfeedback om vad som behöver förbättras
        
    Returns:
        PromptTemplate: Förbättrad promptmall
    """
    template_text = prompt_template.template
    
    # Analysera feedback för att identifiera förbättringsområden
    improvement_areas = []
    
    if "instruktion" in feedback.lower() or "instr" in feedback.lower() or "tydlig" in feedback.lower():
        improvement_areas.append("instructions")
    
    if "format" in feedback.lower() or "json" in feedback.lower() or "struktur" in feedback.lower():
        improvement_areas.append("format")
    
    if "exempel" in feedback.lower() or "demonstr" in feedback.lower():
        improvement_areas.append("examples")
    
    if "fel" in feedback.lower() or "misstag" in feedback.lower() or "problem" in feedback.lower():
        improvement_areas.append("error_prevention")
    
    # Skapa förbättringar baserat på identifierade områden
    for area in improvement_areas:
        if area == "instructions":
            # Förbättra instruktionerna
            if isinstance(prompt_template, ExtractionPrompt):
                prompt_template = prompt_template.with_improved_instructions()
            else:
                # Lägg till tydligare instruktioner för generella mallar
                instruction = "Var extra tydlig och strukturerad i ditt svar. Följ instruktionerna exakt och dubbelkolla att alla krav är uppfyllda."
                prompt_template = prompt_template.with_instruction(instruction)
        
        elif area == "format":
            # Förbättra formatinstruktioner
            if "```json" not in template_text:
                # Lägg till ett exempel på JSON-format om det saknas
                json_example = '{\n  "key": "value",\n  "list": [1, 2, 3]\n}'
                json_instruction = f"\n\nSvara ENDAST i detta JSON-format:\n\n```json\n{json_example}\n```\n"
                
                # Hitta en lämplig plats att lägga till instruktionen
                if "Här är produktdokumentationen:" in template_text:
                    # Lägg till innan dokumentationen
                    parts = template_text.split("Här är produktdokumentationen:")
                    template_text = parts[0] + json_instruction + "Här är produktdokumentationen:" + parts[1]
                else:
                    # Lägg till i slutet av instruktionerna
                    paragraphs = template_text.split("\n\n")
                    introduction_end = min(5, len(paragraphs))
                    template_text = "\n\n".join(paragraphs[:introduction_end]) + json_instruction + "\n\n" + "\n\n".join(paragraphs[introduction_end:])
        
        elif area == "error_prevention":
            # Lägg till felförebyggande tips
            if isinstance(prompt_template, ExtractionPrompt):
                prompt_template = prompt_template.with_error_prevention()
            else:
                # För generella mallar, lägg till generella felförebyggande tips
                error_prevention = """
VANLIGA FEL ATT UNDVIKA:
- Returnera inte text utanför JSON-objektet
- Använd dubbla citattecken för JSON-nycklar och strängvärden
- Kontrollera att JSON-strukturen är korrekt nästlad
- Inkludera alla obligatoriska fält
- Följ det exakta formatet som specificeras
"""
                template_text += error_prevention
        
        elif area == "examples":
            # Skapa exempel om det inte finns
            # För enkelhets skull lägger vi bara till en placeholder här
            # I en verklig implementation skulle detta kunna vara mer avancerat
            if "{examples}" not in template_text and "EXEMPEL" not in template_text:
                example_text = """
EXEMPEL:

INPUT:
```
Exempeltext med information om en produkt...
```

OUTPUT:
```
{
  "field1": "value1",
  "field2": "value2"
}
```
"""
                # Hitta rätt position att lägga till exemplet
                if "Här är produktdokumentationen:" in template_text:
                    # Lägg till innan dokumentationen
                    parts = template_text.split("Här är produktdokumentationen:")
                    template_text = parts[0] + example_text + "Här är produktdokumentationen:" + parts[1]
                else:
                    # Lägg till i slutet av introduktionen
                    paragraphs = template_text.split("\n\n")
                    introduction_end = min(5, len(paragraphs))
                    template_text = "\n\n".join(paragraphs[:introduction_end]) + example_text + "\n\n" + "\n\n".join(paragraphs[introduction_end:])
    
    # Skapa en ny prompt med uppdaterad mall
    if isinstance(prompt_template, ExtractionPrompt) and template_text != prompt_template.template:
        return ExtractionPrompt(
            template=template_text,
            schema=prompt_template.schema,
            name=prompt_template.name + "_improved",
            description=prompt_template.description + " (förbättrad baserat på feedback)",
            version=f"{prompt_template.version}+fb",
            tags=prompt_template.tags + ["improved_from_feedback"],
            extraction_type=prompt_template.extraction_type,
            improved_instructions=prompt_template.improved_instructions,
            error_prevention=prompt_template.error_prevention
        )
    elif isinstance(prompt_template, ValidationPrompt) and template_text != prompt_template.template:
        return ValidationPrompt(
            template=template_text,
            validation_rules=prompt_template.validation_rules,
            name=prompt_template.name + "_improved",
            description=prompt_template.description + " (förbättrad baserat på feedback)",
            version=f"{prompt_template.version}+fb",
            tags=prompt_template.tags + ["improved_from_feedback"]
        )
    elif isinstance(prompt_template, CorrectionPrompt) and template_text != prompt_template.template:
        return CorrectionPrompt(
            template=template_text,
            error_types=prompt_template.error_types,
            name=prompt_template.name + "_improved",
            description=prompt_template.description + " (förbättrad baserat på feedback)",
            version=f"{prompt_template.version}+fb",
            tags=prompt_template.tags + ["improved_from_feedback"]
        )
    elif template_text != prompt_template.template:
        return PromptTemplate(
            template=template_text,
            name=prompt_template.name + "_improved",
            description=prompt_template.description + " (förbättrad baserat på feedback)",
            version=f"{prompt_template.version}+fb",
            tags=prompt_template.tags + ["improved_from_feedback"]
        )
    else:
        # Ingen förändring gjordes
        return prompt_template


def create_conditional_prompt(base_prompt: PromptTemplate, condition_text: str, alternate_instruction: str) -> PromptTemplate:
    """
    Skapar en villkorlig prompt där beteendet ändras baserat på ett visst villkor.
    
    Args:
        base_prompt: Basprompt att utgå från
        condition_text: Texten som beskriver villkoret
        alternate_instruction: Alternativ instruktion att använda om villkoret uppfylls
        
    Returns:
        PromptTemplate: Villkorlig promptmall
    """
    # Skapa villkorlig instruktion
    conditional_text = f"""
OM {condition_text}:
{alternate_instruction}

ANNARS:
Följ standardinstruktionerna nedan.
"""
    
    # Lägg till den villkorliga instruktionen i början av mallen
    new_template = conditional_text + "\n\n" + base_prompt.template
    
    # Skapa rätt typ av prompt baserat på basmallen
    if isinstance(base_prompt, ExtractionPrompt):
        return ExtractionPrompt(
            template=new_template,
            schema=base_prompt.schema,
            name=base_prompt.name + "_conditional",
            description=base_prompt.description + " (med villkorlig logik)",
            version=f"{base_prompt.version}+cond",
            tags=base_prompt.tags + ["conditional"],
            extraction_type=base_prompt.extraction_type,
            improved_instructions=base_prompt.improved_instructions,
            error_prevention=base_prompt.error_prevention
        )
    elif isinstance(base_prompt, ValidationPrompt):
        return ValidationPrompt(
            template=new_template,
            validation_rules=base_prompt.validation_rules,
            name=base_prompt.name + "_conditional",
            description=base_prompt.description + " (med villkorlig logik)",
            version=f"{base_prompt.version}+cond",
            tags=base_prompt.tags + ["conditional"]
        )
    elif isinstance(base_prompt, CorrectionPrompt):
        return CorrectionPrompt(
            template=new_template,
            error_types=base_prompt.error_types,
            name=base_prompt.name + "_conditional",
            description=base_prompt.description + " (med villkorlig logik)",
            version=f"{base_prompt.version}+cond",
            tags=base_prompt.tags + ["conditional"]
        )
    else:
        return PromptTemplate(
            template=new_template,
            name=base_prompt.name + "_conditional",
            description=base_prompt.description + " (med villkorlig logik)",
            version=f"{base_prompt.version}+cond",
            tags=base_prompt.tags + ["conditional"]
        )