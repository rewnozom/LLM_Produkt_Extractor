# Moduldokumentation för LLM-baserad Produktinformationsextraktor

## Övergripande Systemöversikt

Systemet är designat för flexibel, robust och skalbar bearbetning av produktdata genom flera sammankopplade komponenter.

```mermaid
graph TD
    A[WorkflowManager] --> B[ProcessingQueue]
    A --> C[BatchProcessor]
    A --> D[JobScheduler]
    A --> E[Workers]
    A --> F[ProductProcessor]
    A --> G[PromptManager]
    A --> H[SearchIndex]
    
    B --> I{Jobbhantering}
    C --> J{Batchbearbetning}
    D --> K{Schemaläggning}
    E --> L{Parallell Bearbetning}
    F --> M{Produktextraktion}
    G --> N{Promptoptimering}
    H --> O{Produktsökning}
```

## Kärnkomponenter

### 1. WorkflowManager
Central hanterare som koordinerar alla systemkomponenter och arbetsflöden.

```mermaid
classDiagram
class WorkflowManager {
    +start()
    +stop()
    +pause()
    +resume()
    +process_product()
    +enqueue_product()
    +schedule_product()
    +process_directory()
    +process_csv()
}
```

### 2. ProcessingQueue
Hanterar jobb med prioritering och trådsäker köhantering.

```mermaid
stateDiagram-v2
    [*] --> Pending : Jobb skapas
    Pending --> InQueue : Läggs till
    InQueue --> Processing : Hämtas av Worker
    Processing --> Completed : Framgångsrikt
    Processing --> Failed : Misslyckas
    Failed --> Retry : Återförsök möjligt
    Retry --> Pending
    Completed --> [*]
```

### 3. BatchProcessor
Möjliggör massbearbetning av produkter från olika källor.

```mermaid
flowchart LR
    A[Importkälla] --> B{BatchProcessor}
    B --> C[Katalog]
    B --> D[CSV]
    B --> E[Manuell Lista]
    
    C --> F[Jobskapande]
    D --> F
    E --> F
    
    F --> G[Köhantering]
    G --> H[Bearbetning]
    H --> I[Rapportering]
```

### 4. JobScheduler
Schemalägger och hanterar jobb över tid.

```mermaid
timeline
    title Jobbschemaläggning
    Engångsjobb : Specifik tidpunkt
    Återkommande jobb : Regelbundna intervall
    Prioriterade jobb : Dynamisk prioritering
```

### 5. Workers
Parallella bearbetningsenheter för produktextraktion.

```mermaid
flowchart TD
    A[Worker Pool] --> B[Hämta Jobb]
    B --> C{Bearbetningsstatus}
    C --> |Framgång| D[Spara Resultat]
    C --> |Fel| E[Hantera Återförsök]
    D --> F[Uppdatera Statistik]
    E --> G[Omplacera Jobb]
```

## Nyckelarkitekturprinciper

1. **Trådsäkerhet**: Implementerad genom låsmekanismer och koordinerade operationer
2. **Flexibel Prioritering**: Dynamisk jobbprioritering
3. **Robust Felhantering**: Återförsöksmekanismer och detaljerad loggning
4. **Skalbarhet**: Oberoende komponenter möjliggör horisontell skalning

## Arbetsflödesstrategi

```mermaid
journey
    title Produktextraktionsprocess
    section Förberedelse
        Importera data: 1: Datakälla
        Identifiera produkt: 2: Förbearbetning
    section Bearbetning  
        Extrahera information: 3: LLM-analys
        Validera innehåll: 4: Kvalitetskontroll
        Strukturera data: 5: Datamodellering
    section Resultathantering
        Spara strukturerat: 6: Persistent lagring
        Indexera: 7: Sökoptimering
        Generera rapport: 8: Dokumentation
```

## Funktioner:

- Dynamisk promptoptimering
- Automatisk sökindexering
- Relationsgrafgenerering
- Automatiserad rapportering
- Konfigurerbar bearbetningskontext

## Säkerhets- och Prestandaöverväganden

1. Trådsäkra datastrukturer
2. Konfigurerbara timeouts
3. Mekanismer för mjuk nedstängning
4. Minneseffektiv bearbetning
5. Asynkron jobbhantering

## Skalbarhetspotential

- Horisontell skalning genom worker-pool
- Dynamisk resursallokering
- Stöd för distribuerad bearbetning
- Konfigurerbar parallellism

## Extensibility

Systemet är konstruerat med löst kopplade komponenter som möjliggör:
- Enkla tillägg av nya bearbetningsmoduler
- Anpassningsbara extraktionsstrategier
- Utbytbara underkomponenter

----



1. **Söknings- och Relationsfunktioner**
   - `query_products_by_attribute()`: Flexibel produktsökning
   - `query_products_with_relations()`: Relationsbaserad sökning
   - `find_related_products_graph()`: Generera produktrelationsgraf
   - `export_relation_graph()`: Exportera relationsdata

2. **Rapporterings- och Exportfunktioner**
   - `generate_html_dashboard()`: Interaktiv statusöversikt
   - `generate_data_report()`: Omfattande datasammanställning
   - `export_product_data()`: Detaljerad produktdataexport
   - `generate_compatibility_report()`: Kompatibilitetsanalys

3. **Konfigurations- och Systemhantering**
   - `update_config()`: Dynamisk konfigurationsuppdatering
   - `export_config()`: Konfigurationsexport
   - `reload_config()`: Omkonfigurering under körning
   - `execute_script()`: Skriptkörning i systemkontext



```mermaid
mindmap
  root((Funktioner))
    Sökning
      Attributbaserad
      Relationsbaserad
      Grafgenerering
    Rapportering
      HTML Dashboard
      Datasammanställning
      Produktexport
      Kompatibilitetsanalys
    Systemhantering
      Dynamisk Konfiguration
      Konfigurationsexport
      Omkonfigurering
      Skriptkörning
```

