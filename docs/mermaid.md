# Arbetsflödessammanfattningar för LLM-baserad Produktinformationsextraktor

## Övergripande arbetsflöde

1. **Inläsning av produktdata**: Systemet läser in produktbeskrivningar från markdown-filer
2. **Bearbetning med LLM**: Texten skickas till en lokal AI (LLM) som extraherar värdefull information
3. **Strukturering**: AI-svaren omvandlas till strukturerade data om kompatibilitet och specifikationer
4. **Validering**: Systemet kontrollerar att informationen är komplett och korrekt
5. **Lagring**: Resultaten sparas i strukturerade filer för enkel åtkomst
6. **Rapportering**: Systemet skapar detaljerade rapporter om det extraherade innehållet

```mermaid
flowchart TD
    Start([Start]) --> ReadFiles[Läs produktfiler]
    ReadFiles --> ProcessLLM[Skicka till AI/LLM]
    ProcessLLM --> ParseResults[Tolka AI-svar]
    ParseResults --> Validate{Validera data}
    Validate -->|Valid| SaveResults[Spara resultat]
    Validate -->|Invalid| FixData[Försök korrigera]
    FixData --> Validate
    SaveResults --> Report[Skapa rapport]
    Report --> End([Slut])
```

## Start och konfiguration

1. **Läs konfiguration**: Ladda inställningar från config-filen
2. **Kontrollera LLM-tjänst**: Verifiera anslutning till lokal AI (Ollama, LM Studio, etc.)
3. **Skapa arbetsmiljö**: Förbered kataloger och loggning
4. **Initialisera komponenter**: Starta nödvändiga system

```mermaid
flowchart TD
    Start([Start]) --> ReadConfig[Läs konfigurationsfil]
    ReadConfig --> CheckLLM{Kontrollera LLM-tjänst}
    CheckLLM -->|OK| PrepDirs[Förbered kataloger]
    CheckLLM -->|Fel| Fallback[Försök fallback-tjänst]
    Fallback --> CheckFallback{Fallback OK?}
    CheckFallback -->|Ja| PrepDirs
    CheckFallback -->|Nej| Exit([Avsluta med fel])
    PrepDirs --> InitLog[Konfigurera loggning]
    InitLog --> InitComponents[Initialisera komponenter]
    InitComponents --> Ready([Systemet redo])
```

## Filbearbetning

1. **Kontrollera storlek**: Systemet avgör om filen behöver delas upp
2. **Delning (vid behov)**: Stora filer delas i mindre delar med överlappning
3. **LLM-bearbetning**: Varje del skickas till AI-tjänsten
4. **Sammanfogning**: Resultat från alla delar sammanställs till ett komplett resultat

```mermaid
flowchart TD
    Start([Start filbearbetning]) --> CheckSize{Kontrollera filstorlek}
    CheckSize -->|Liten fil| ProcessWhole[Bearbeta hela filen]
    CheckSize -->|Stor fil| SplitFile[Dela upp filen]
    SplitFile --> ProcessChunks[Bearbeta varje del]
    ProcessChunks --> MergeResults[Sammanfoga resultat]
    ProcessWhole --> ValidateResults{Validera resultat}
    MergeResults --> ValidateResults
    ValidateResults -->|Godkänt| SaveResults[Spara strukturerat resultat]
    ValidateResults -->|Underkänt| FixResults[Försök korrigera]
    FixResults --> ValidateResults
    SaveResults --> End([Klar])
```

## AI-interaktion

1. **Förbereda prompt**: Skapa en specialiserad instruktion till AI-modellen
2. **Skicka förfrågan**: Kommunicera med den lokala AI-tjänsten
3. **Hantera svar**: Tolka AI:ns svar och extrahera strukturerad information
4. **Felhantering**: Automatiska återförsök vid tillfälliga fel

```mermaid
flowchart TD
    Start([Starta AI-interaktion]) --> PrepPrompt[Förbered prompt]
    PrepPrompt --> SendRequest[Skicka förfrågan till LLM]
    SendRequest --> CheckResponse{Kontrollera svar}
    CheckResponse -->|Lyckat| ParseJSON[Extrahera JSON-data]
    CheckResponse -->|Misslyckat| Retry{Försök igen?}
    Retry -->|Ja| Backoff[Exponentiell backoff]
    Backoff --> SendRequest
    Retry -->|Nej| FallbackLLM{Använd fallback LLM?}
    FallbackLLM -->|Ja| SwitchLLM[Byt till fallback-modell]
    SwitchLLM --> SendRequest
    FallbackLLM -->|Nej| Fail([Misslyckad interaktion])
    ParseJSON --> ValidateFormat{Korrekt format?}
    ValidateFormat -->|Ja| Success([Lyckad interaktion])
    ValidateFormat -->|Nej| FixFormat[Skicka korrigeringsprompt]
    FixFormat --> SendRequest
```

## Parallell bearbetning

1. **Skapa jobbkö**: Bygg en kö med produkter att bearbeta
2. **Starta arbetare**: Initiera flera parallella bearbetningstrådar
3. **Fördelning**: Arbetare hämtar jobb från kön baserat på prioritet
4. **Statusspårning**: Övervaka framsteg och identifiera problem

```mermaid
flowchart TD
    Start([Start parallell bearbetning]) --> CreateQueue[Skapa jobbkö]
    CreateQueue --> EnqueueJobs[Lägg produkter i kö]
    EnqueueJobs --> StartWorkers[Starta arbetartrådar]
    StartWorkers --> ProcessLoop[Fördelningsloop]
    
    subgraph "För varje arbetare"
    WaitJob[Vänta på jobb] --> GetJob[Hämta nästa jobb]
    GetJob --> ProcessJob[Bearbeta produkt]
    ProcessJob --> SaveResult[Spara resultat]
    SaveResult --> UpdateStatus[Uppdatera status]
    UpdateStatus --> WaitJob
    end
    
    ProcessLoop --> Monitor[Övervaka framsteg]
    Monitor --> CheckComplete{Alla jobb klara?}
    CheckComplete -->|Nej| Monitor
    CheckComplete -->|Ja| GenerateReport[Skapa slutrapport]
    GenerateReport --> End([Klar])
```

## Batch-bearbetning

1. **Inläsning av produktlista**: Läs in en lista med produkter från katalog eller CSV
2. **Gruppering**: Dela upp produkter i hanterbara batcher
3. **Schemaläggning**: Lägg batcher i jobbkön med prioritet
4. **Rapportering**: Skapa batch-specifika rapporter

```mermaid
flowchart TD
    Start([Start batch-bearbetning]) --> LoadList[Läs produktlista]
    LoadList --> ValidateEntries[Validera produktposter]
    ValidateEntries --> CreateBatches[Skapa batcher]
    CreateBatches --> ScheduleJobs[Schemalägg batchjobb]
    ScheduleJobs --> MonitorProgress[Övervaka framsteg]
    MonitorProgress --> CheckBatch{Batch klar?}
    CheckBatch -->|Nej| MonitorProgress
    CheckBatch -->|Ja| GenerateBatchReport[Skapa batchrapport]
    GenerateBatchReport --> CheckAllDone{Alla batcher klara?}
    CheckAllDone -->|Nej| MonitorProgress
    CheckAllDone -->|Ja| CreateSummary[Skapa sammanfattande rapport]
    CreateSummary --> End([Klar])
```

## Extrahering av kompatibilitetsinformation

1. **Specialiserad prompt**: Skicka en detaljerad förfrågan om produktkopplingar
2. **Tolkning**: Identifiera vilka produkter som är kompatibla med varandra
3. **Kvalitetskontroll**: Filtrera bort osäkra kopplingar
4. **Strukturering**: Organisera information i användbart format

```mermaid
flowchart TD
    Start([Start kompatibilitetsextrahering]) --> PrepPrompt[Förbered kompatibilitetsprompt]
    PrepPrompt --> SendLLM[Skicka till LLM]
    SendLLM --> ParseResponse[Tolka respons]
    ParseResponse --> ExtractRelations[Extrahera relationer]
    ExtractRelations --> FilterConfidence{Filtrera förtroende}
    FilterConfidence -->|Hög tilltro| KeepRelation[Behåll relation]
    FilterConfidence -->|Låg tilltro| DiscardRelation[Förkasta relation]
    KeepRelation --> CollectRelations[Samla alla relationer]
    DiscardRelation --> LogDiscarded[Logga förkastade]
    LogDiscarded --> CollectRelations
    CollectRelations --> StructureData[Strukturera data]
    StructureData --> NormalizeProducts[Normalisera produktnamn]
    NormalizeProducts --> AddMetadata[Lägg till metadata]
    AddMetadata --> End([Klar])
```

## Extrahering av tekniska specifikationer

1. **Teknisk prompt**: Skicka en förfrågan om produktens tekniska egenskaper
2. **Kategorisering**: Gruppera specifikationer i kategorier (dimensioner, elektriska, etc.)
3. **Standardisering**: Normalisera enheter och värden
4. **Validering**: Kontrollera fullständighet och rimlighet

```mermaid
flowchart TD
    Start([Start teknisk extrahering]) --> PrepPrompt[Förbered teknisk prompt]
    PrepPrompt --> SendLLM[Skicka till LLM]
    SendLLM --> ParseResponse[Tolka respons]
    ParseResponse --> ExtractSpecs[Extrahera specifikationer]
    ExtractSpecs --> CategorizeSpecs[Kategorisera specifikationer]
    CategorizeSpecs --> StandardizeUnits[Standardisera enheter]
    StandardizeUnits --> ValidateValues{Validera värden}
    ValidateValues -->|Giltigt| KeepSpec[Behåll specifikation]
    ValidateValues -->|Ogiltigt| FixValue[Försök korrigera värde]
    FixValue --> ValidateValues
    KeepSpec --> CollectSpecs[Samla alla specifikationer]
    CollectSpecs --> FormatOutput[Formatera utdata]
    FormatOutput --> End([Klar])
```

## FAQ-svarsgeneration

1. **Frågeanalys**: Identifiera vilken typ av information som efterfrågas
2. **Datahämtning**: Hämta relevanta extraherade data
3. **Svarsformatering**: Skapa ett strukturerat och informativt svar
4. **Formatering**: Presentera svaret i läsbart format

```mermaid
flowchart TD
    Start([Start FAQ-generering]) --> AnalyzeQuestion[Analysera fråga]
    AnalyzeQuestion --> DetermineType{Vilken typ av fråga?}
    DetermineType -->|Kompatibilitet| FetchCompat[Hämta kompatibilitetsdata]
    DetermineType -->|Teknisk| FetchTech[Hämta tekniska specifikationer]
    DetermineType -->|Generell| FetchAll[Hämta all produktinfo]
    FetchCompat --> FilterRelevant[Filtrera relevant information]
    FetchTech --> FilterRelevant
    FetchAll --> FilterRelevant
    FilterRelevant --> StructureAnswer[Strukturera svar]
    StructureAnswer --> FormatMarkdown[Formatera i Markdown]
    FormatMarkdown --> CheckCompleteness{Fullständigt svar?}
    CheckCompleteness -->|Ja| SaveAnswer[Spara svar]
    CheckCompleteness -->|Nej| AddDisclaimer[Lägg till disclaimer]
    AddDisclaimer --> SaveAnswer
    SaveAnswer --> End([Klar])
```

## Felhantering och återhämtning

1. **Felidentifiering**: Upptäck problem under bearbetningen
2. **Kategorisering**: Avgör typ av fel och allvarlighetsgrad
3. **Återhämtning**: Implementera lämplig återhämtningsstrategi
4. **Loggning**: Spåra fel för senare analys

```mermaid
flowchart TD
    Start([Start felhantering]) --> DetectIssue[Upptäck problem]
    DetectIssue --> CategorizeError{Kategorisera fel}
    CategorizeError -->|LLM-tjänst| HandleLLM[Hantera LLM-fel]
    CategorizeError -->|Filoperationer| HandleIO[Hantera I/O-fel]
    CategorizeError -->|Formatering| HandleFormat[Hantera formatfel]
    CategorizeError -->|Oväntat| HandleUnexpected[Hantera oväntat fel]
    
    HandleLLM --> RetryLLM{Försök igen?}
    RetryLLM -->|Ja| Backoff[Exponentiell väntetid]
    RetryLLM -->|Nej| FallbackLLM[Använd alternativ LLM]
    Backoff --> LogRetry[Logga återförsök]
    
    HandleIO --> CheckCritical{Kritiskt?}
    CheckCritical -->|Ja| AbortJob[Avbryt jobb]
    CheckCritical -->|Nej| RecoverFile[Försök återhämta fil]
    
    HandleFormat --> AttemptCorrection[Försök korrigera format]
    HandleUnexpected --> SafeState[Återställ till säkert läge]
    
    LogRetry --> End([Slutför felhantering])
    FallbackLLM --> End
    AbortJob --> End
    RecoverFile --> End
    AttemptCorrection --> End
    SafeState --> End
```

## Rapportering och analys

1. **Datainsamling**: Samla statistik från bearbetning
2. **Visualisering**: Skapa visuella sammanställningar
3. **Detaljanalys**: Generera djupgående rapporter
4. **Export**: Spara data i läsbara format (JSON, Markdown)

```mermaid
flowchart TD
    Start([Start rapportering]) --> CollectStats[Samla statistik]
    CollectStats --> ComputeMetrics[Beräkna nyckeltal]
    ComputeMetrics --> GenerateSummary[Skapa sammanfattning]
    GenerateSummary --> CreateVisuals[Skapa visualiseringar]
    CreateVisuals --> GenerateReports[Skapa rapporter]
    GenerateReports --> ExportJSON[Exportera JSON]
    ExportJSON --> ExportMarkdown[Exportera Markdown]
    ExportMarkdown --> NotifyComplete[Meddela färdig]
    NotifyComplete --> End([Klar])
```

## Användarinteraktion via CLI

1. **Kommandotolkning**: Tolka användarens kommando och argument
2. **Konfiguration**: Läs och tillämpa konfigurationsalternativ
3. **Feedback**: Ge användaren återkoppling om framsteg
4. **Resultatpresentation**: Visa och spara resultat på begärt sätt

```mermaid
flowchart TD
    Start([Användarinteraktion]) --> ParseArgs[Tolka kommandoradsargument]
    ParseArgs --> IdentifyCommand{Vilket kommando?}
    IdentifyCommand -->|process-product| SingleProduct[Bearbeta enskild produkt]
    IdentifyCommand -->|process-directory| Directory[Bearbeta katalog]
    IdentifyCommand -->|process-csv| CSV[Bearbeta CSV-fil]
    IdentifyCommand -->|start-workflow| Workflow[Starta arbetsflöde]
    IdentifyCommand -->|generate-faq| FAQ[Generera FAQ-svar]
    IdentifyCommand -->|test-connection| TestLLM[Testa LLM-anslutning]
    
    SingleProduct --> GetConfig[Hämta konfiguration]
    Directory --> GetConfig
    CSV --> GetConfig
    Workflow --> GetConfig
    FAQ --> GetConfig
    TestLLM --> GetConfig
    
    GetConfig --> SetupLogging[Konfigurera loggning]
    SetupLogging --> InitComponents[Initialisera komponenter]
    InitComponents --> ExecuteCommand[Utför kommando]
    ExecuteCommand --> ShowProgress[Visa framsteg]
    ShowProgress --> DisplayResults[Visa resultat]
    DisplayResults --> End([Klar])
```


Här är fler arbetsflödessammanfattningar och mermaid-diagram som täcker resterande aspekter av systemet:

## Kontinuerlig bearbetning

1. **Katalogövervakning**: Systemet övervakar en katalog för nya jobbfiler
2. **Automatisk upptäckt**: Nya jobb läggs automatiskt till i kön
3. **Statusuppdatering**: Periodiska statusuppdateringar visas i terminalen
4. **Tillståndsbevarande**: Jobbtillstånd sparas för att klara omstarter

```mermaid
flowchart TD
    Start([Start kontinuerlig bearbetning]) --> WatchDir[Övervaka jobbkatalog]
    WatchDir --> CheckNew{Nya jobbfiler?}
    CheckNew -->|Ja| ParseJob[Tolka jobbfil]
    CheckNew -->|Nej| Wait[Vänta intervall]
    Wait --> CheckNew
    
    ParseJob --> ValidateJob{Giltig jobbfil?}
    ValidateJob -->|Ja| QueueJob[Lägg i kö]
    ValidateJob -->|Nej| MoveToError[Flytta till felkatalog]
    
    QueueJob --> ProcessQueuedJobs[Bearbeta jobb i kö]
    MoveToError --> LogError[Logga fel]
    
    ProcessQueuedJobs --> UpdateStatus[Uppdatera status]
    LogError --> UpdateStatus
    
    UpdateStatus --> SaveState[Spara tillstånd]
    SaveState --> DisplayStatus[Visa status]
    DisplayStatus --> Wait
```

## Produktidentifikation och normalisering

1. **Extrahering av produktidentifierare**: Systemet upptäcker produkt-ID och artikelnummer
2. **Standardisering**: Produktnamn formateras enhetligt
3. **Uppslag**: Relaterade produkter matchas mot kända produktdatabaser
4. **Referensvalidering**: Kontrollera att produktreferenser är giltiga

```mermaid
flowchart TD
    Start([Start produktnormalisering]) --> ExtractIDs[Extrahera produkt-ID]
    ExtractIDs --> ParseArticleNumbers[Tolka artikelnummer]
    ParseArticleNumbers --> StandardizeNames[Standardisera produktnamn]
    StandardizeNames --> RemoveDuplicates[Ta bort dubbletter]
    RemoveDuplicates --> LookupProducts{Sök i produktdatabas}
    LookupProducts -->|Hittad| AssignKnownProduct[Använd känd produkt]
    LookupProducts -->|Ej hittad| StoreAsNew[Lagra som ny produkt]
    AssignKnownProduct --> ValidateReferences[Validera produktreferenser]
    StoreAsNew --> ValidateReferences
    ValidateReferences --> CleanOutput[Rensa utdata]
    CleanOutput --> End([Klar])
```

## Schemaläggning och prioritering

1. **Prioritetsklassificering**: Jobb kategoriseras efter prioritet
2. **Tidsberoende schemaläggning**: Jobb kan schemalaggas för framtida körning
3. **Dynamisk omprioritering**: Prioriteter kan justeras baserat på systembelastning
4. **Resursallokering**: CPU och minnestilldelning baserat på jobbprioritet

```mermaid
flowchart TD
    Start([Start schemaläggning]) --> ClassifyJobs[Klassificera jobb]
    ClassifyJobs --> AssignPriority[Tilldela prioritet]
    AssignPriority --> TimeBasedQueuing{Tidsbaserad?}
    TimeBasedQueuing -->|Ja| ScheduleForLater[Schemalägg för senare]
    TimeBasedQueuing -->|Nej| QueueImmediately[Köa direkt]
    
    ScheduleForLater --> MonitorSchedule[Övervaka schema]
    QueueImmediately --> MonitorQueue[Övervaka kö]
    
    MonitorSchedule --> CheckReadyTime{Tid att köra?}
    CheckReadyTime -->|Ja| MoveToQueue[Flytta till aktiv kö]
    CheckReadyTime -->|Nej| WaitMore[Fortsätt vänta]
    WaitMore --> MonitorSchedule
    
    MoveToQueue --> MonitorQueue
    MonitorQueue --> CheckSystemLoad{Hög belastning?}
    CheckSystemLoad -->|Ja| ReprioritizeJobs[Omprioritera jobb]
    CheckSystemLoad -->|Nej| AllocateResources[Tilldela resurser]
    
    ReprioritizeJobs --> AllocateResources
    AllocateResources --> ExecuteJob[Kör jobb]
    ExecuteJob --> End([Klar])
```

## Throttling och belastningshantering

1. **Begränsning av LLM-anrop**: Kontrollerad takt för förfrågningar till LLM-tjänsten
2. **Övervakning av systemresurser**: Mätning av CPU, minne och nätverksutnyttjande
3. **Dynamisk justering**: Anpassning av bearbetningstakten baserat på aktuell belastning
4. **Backoff-strategier**: Exponentiell ökning av väntetid vid tjänstebegränsningar

```mermaid
flowchart TD
    Start([Start throttling]) --> MonitorResources[Övervaka resurser]
    MonitorResources --> TrackLLMCalls[Spåra LLM-anrop]
    TrackLLMCalls --> CheckRate{Över gränsvärde?}
    CheckRate -->|Ja| ThrottleRequests[Begränsa anrop]
    CheckRate -->|Nej| CheckSystemLoad{Hög belastning?}
    
    ThrottleRequests --> ImplementBackoff[Implementera backoff]
    ImplementBackoff --> LogThrottling[Logga begränsning]
    LogThrottling --> WaitBeforeContinuing[Vänta innan fortsättning]
    
    CheckSystemLoad -->|Ja| ReduceWorkers[Minska arbetarantal]
    CheckSystemLoad -->|Nej| OptimizeLoad[Optimera belastning]
    
    ReduceWorkers --> MonitorRecovery[Övervaka återhämtning]
    OptimizeLoad --> AdjustBatchSize[Justera batchstorlek]
    
    WaitBeforeContinuing --> ResumeProcessing[Återuppta bearbetning]
    MonitorRecovery --> ResumeProcessing
    AdjustBatchSize --> ResumeProcessing
    
    ResumeProcessing --> End([Klar])
```

## Validering och kvalitetskontroll

1. **Schemakontroll**: Verifiering att extraherad data följer förväntad struktur
2. **Innehållsvalidering**: Kontroll av att innehållet är rimligt och konsekvent
3. **Förtroendefiltrering**: Filtrering baserat på LLM:s förtroende för extraherad information
4. **Korrigeringsåtgärder**: Automatiska försök att rätta till problem

```mermaid
flowchart TD
    Start([Start validering]) --> CheckSchema[Kontrollera schema]
    CheckSchema --> ValidateStructure{Korrekt struktur?}
    ValidateStructure -->|Ja| CheckRequiredFields[Kontrollera obligatoriska fält]
    ValidateStructure -->|Nej| FixStructure[Fixa struktur]
    
    FixStructure --> CheckRequiredFields
    CheckRequiredFields --> ValidateFields{Alla fält finns?}
    ValidateFields -->|Ja| CheckContent[Validera innehåll]
    ValidateFields -->|Nej| FixFields[Fixa saknade fält]
    
    FixFields --> CheckContent
    CheckContent --> FilterConfidence[Filtrera efter förtroende]
    FilterConfidence --> CheckConsistency[Kontrollera konsistens]
    
    CheckConsistency --> ValidateConsistency{Konsistent?}
    ValidateConsistency -->|Ja| ValidateRelations[Validera relationer]
    ValidateConsistency -->|Nej| FixConsistency[Fixa inkonsekvenser]
    
    FixConsistency --> ValidateRelations
    ValidateRelations --> FinalCheck{Allt godkänt?}
    FinalCheck -->|Ja| MarkValidated[Markera som validerad]
    FinalCheck -->|Nej| MarkPartial[Markera som delvis validerad]
    
    MarkValidated --> LogValidation[Logga valideringsresultat]
    MarkPartial --> LogValidation
    LogValidation --> End([Klar])
```

## Datalagring och filhantering

1. **Strukturerade format**: Lagring av extraktion i JSON och andra strukturerade format
2. **Katalogorganisering**: Organisering av filer i logiska katalogstrukturer
3. **Versionshantering**: Spårning av ändringar över tid
4. **Säkerhetskopiering**: Automatisk säkerhetskopiering av viktiga data

```mermaid
flowchart TD
    Start([Start datalagring]) --> CreateDirStructure[Skapa katalogstruktur]
    CreateDirStructure --> SaveJSON[Spara JSON-data]
    SaveJSON --> SaveMarkdown[Spara Markdown-rapport]
    SaveMarkdown --> OrganizeByProduct[Organisera efter produkt]
    
    OrganizeByProduct --> CheckFileExists{Fil finns redan?}
    CheckFileExists -->|Ja| VersionFile[Versionshantera fil]
    CheckFileExists -->|Nej| SaveNewFile[Spara ny fil]
    
    VersionFile --> BackupFiles[Säkerhetskopiera filer]
    SaveNewFile --> BackupFiles
    
    BackupFiles --> CleanupOld{Städa gamla filer?}
    CleanupOld -->|Ja| RemoveOldVersions[Ta bort gamla versioner]
    CleanupOld -->|Nej| SkipCleanup[Behåll alla versioner]
    
    RemoveOldVersions --> UpdateIndex[Uppdatera filindex]
    SkipCleanup --> UpdateIndex
    
    UpdateIndex --> VerifyFiles[Verifiera filintegritet]
    VerifyFiles --> End([Klar])
```

## Återhämtning vid systemkrasch

1. **Tillståndsspårning**: Kontinuerlig loggning av systemets tillstånd
2. **Checkpoint-skapande**: Regelbunden lagring av säkra tillståndspunkter
3. **Återställning**: Process för att återställa systemet efter krasch
4. **Återupptagning**: Förmåga att fortsätta bearbetning från senaste säkra punkt

```mermaid
flowchart TD
    Start([Start återhämtning]) --> DetectCrash[Upptäck systemkrasch]
    DetectCrash --> LoadState[Ladda senaste tillstånd]
    LoadState --> FindCheckpoint[Hitta senaste checkpoint]
    FindCheckpoint --> ValidateState{Giltigt tillstånd?}
    
    ValidateState -->|Ja| RecoverQueue[Återställ jobbkö]
    ValidateState -->|Nej| FindPrevious[Hitta tidigare checkpoint]
    FindPrevious --> ValidateState
    
    RecoverQueue --> IdentifyProcessed[Identifiera bearbetade jobb]
    IdentifyProcessed --> RestoreWorkers[Återställ arbetartrådar]
    RestoreWorkers --> RecoverFiles[Återställ påverkade filer]
    
    RecoverFiles --> VerifyRecovery{Lyckad återställning?}
    VerifyRecovery -->|Ja| ResumePipeline[Återuppta pipeline]
    VerifyRecovery -->|Nej| SafeRestart[Gör säker omstart]
    
    SafeRestart --> NotifyAdmin[Meddela administratör]
    ResumePipeline --> LogRecovery[Logga återhämtning]
    
    NotifyAdmin --> End([Klar])
    LogRecovery --> End
```

## API-integrering

1. **Endpoint-konfguration**: Konfigurering av API-ändpunkter för externa system
2. **Datapublicering**: Tillgängliggörande av extraherad information via API
3. **Verifieringsflöde**: Kontroll av behörighet och datakvalitet
4. **Svarsgenerering**: Struktureringav API-svar

```mermaid
flowchart TD
    Start([Start API-hantering]) --> ConfigEndpoints[Konfigurera endpoints]
    ConfigEndpoints --> SetupAuthentication[Konfigurera autentisering]
    SetupAuthentication --> SetupRateLimit[Konfigurera gränsvärden]
    
    SetupRateLimit --> HandleRequest[Hantera API-förfrågan]
    HandleRequest --> ValidateRequest{Validera förfrågan}
    ValidateRequest -->|Giltig| AuthorizeRequest{Auktoriserad?}
    ValidateRequest -->|Ogiltig| ReturnError[Returnera felmeddelande]
    
    AuthorizeRequest -->|Ja| ProcessRequest[Bearbeta förfrågan]
    AuthorizeRequest -->|Nej| ReturnUnauthorized[Returnera ej auktoriserad]
    
    ProcessRequest --> FetchData[Hämta begärd data]
    FetchData --> FormatResponse[Formatera svar]
    FormatResponse --> CacheResponse[Cacha svar]
    
    CacheResponse --> ReturnResponse[Returnera svar]
    ReturnError --> LogError[Logga fel]
    ReturnUnauthorized --> LogError
    
    ReturnResponse --> LogRequest[Logga förfrågan]
    LogError --> LogRequest
    LogRequest --> End([Klar])
```

## Nyckelterm-extraktion

1. **Termidentifiering**: Upptäckt av viktiga termer i produktdokumentation
2. **Begreppsklassificering**: Kategorisering av termer (produktnamn, egenskaper, tekniska termer)
3. **Relationsanalys**: Spårning av hur termer relaterar till varandra
4. **Lexikonbyggande**: Skapande av produktspecifik ordlista

```mermaid
flowchart TD
    Start([Start termextraktion]) --> TokenizeText[Tokenisera text]
    TokenizeText --> IdentifyTerms[Identifiera potentiella termer]
    IdentifyTerms --> FilterCommon[Filtrera vanliga ord]
    FilterCommon --> ClassifyTerms[Klassificera termer]
    
    ClassifyTerms --> ProductNames[Produktnamn]
    ClassifyTerms --> TechnicalTerms[Tekniska termer]
    ClassifyTerms --> FeatureTerms[Egenskapstermer]
    
    ProductNames --> AnalyzeCooccurrence[Analysera samförekomst]
    TechnicalTerms --> AnalyzeCooccurrence
    FeatureTerms --> AnalyzeCooccurrence
    
    AnalyzeCooccurrence --> BuildRelationGraph[Bygg relationsgraf]
    BuildRelationGraph --> CalculateImportance[Beräkna termviktighet]
    CalculateImportance --> FilterByRelevance[Filtrera efter relevans]
    
    FilterByRelevance --> BuildLexicon[Bygg produktlexikon]
    BuildLexicon --> LinkToProducts[Länka till produkter]
    LinkToProducts --> End([Klar])
```

## Visualisering av kompatibilitetsrelationer

1. **Dataförberedelse**: Bearbetning av extraherad information för visualisering
2. **Grafgenerering**: Skapande av kompatibilitetsgraf
3. **Nodkategorisering**: Färgkodning och gruppering av produkter
4. **Exportformat**: Generering av grafer i olika format (SVG, HTML, etc.)

```mermaid
flowchart TD
    Start([Start visualisering]) --> PrepareData[Förbereda kompatibilitetsdata]
    PrepareData --> BuildGraph[Skapa relationsgraf]
    BuildGraph --> ClassifyNodes[Klassificera noder]
    ClassifyNodes --> ColorCodeRelations[Färgkoda relationer]
    
    ColorCodeRelations --> ApplyLayout[Tillämpa graflayout]
    ApplyLayout --> AddLegend[Lägg till förklaring]
    AddLegend --> AddMetadata[Lägg till metadata]
    
    AddMetadata --> GenerateSVG[Generera SVG]
    GenerateSVG --> GenerateHTML[Generera interaktiv HTML]
    GenerateHTML --> OptimizeSize[Optimera filstorlek]
    
    OptimizeSize --> ExportFiles[Exportera filer]
    ExportFiles --> End([Klar])
```

## Systemövervakning och diagnostik

1. **Prestandamätning**: Insamling av prestandarelaterade mätvärden
2. **Hälsokontroll**: Regelbundna kontroller av systemets hälsotillstånd
3. **Aviseringar**: Automatiska meddelanden vid problem
4. **Diagnostikverktyg**: Hjälpmedel för att identifiera och lösa problem

```mermaid
flowchart TD
    Start([Start övervakning]) --> CollectMetrics[Samla systemmetrik]
    CollectMetrics --> TrackPerformance[Spåra prestanda]
    TrackPerformance --> MonitorLLM[Övervaka LLM-tjänster]
    MonitorLLM --> CheckDiskSpace[Kontrollera diskutrymme]
    
    CheckDiskSpace --> HealthCheck{Systemhälsa OK?}
    HealthCheck -->|Ja| LogStatus[Logga normal status]
    HealthCheck -->|Nej| DiagnoseIssue[Diagnostisera problem]
    
    DiagnoseIssue --> IssueType{Problemtyp?}
    IssueType -->|LLM| DiagnoseLLM[Diagnostisera LLM]
    IssueType -->|Fil| DiagnoseIO[Diagnostisera I/O]
    IssueType -->|Resurs| DiagnoseResource[Diagnostisera resursbrist]
    
    DiagnoseLLM --> AttemptLLMFix[Försök fixa LLM-problem]
    DiagnoseIO --> AttemptIOFix[Försök fixa I/O-problem]
    DiagnoseResource --> AttemptResourceFix[Försök fixa resursproblem]
    
    AttemptLLMFix --> CheckFixed{Problem löst?}
    AttemptIOFix --> CheckFixed
    AttemptResourceFix --> CheckFixed
    
    CheckFixed -->|Ja| LogRecovery[Logga återhämtning]
    CheckFixed -->|Nej| SendAlert[Skicka avisering]
    
    LogStatus --> SaveMetrics[Spara metriker]
    LogRecovery --> SaveMetrics
    SendAlert --> SaveMetrics
    
    SaveMetrics --> End([Klar])
```

## Användargränssnittsinteraktion

1. **Kommandotolkning**: Analys av användarkommando
2. **Parametervalidering**: Kontroll av användarindata
3. **Formaterad utskrift**: Visning av resultat i läsbar format
4. **Färgkodning**: Visuell förstärkning av viktig information

```mermaid
flowchart TD
    Start([Start UI-interaktion]) --> ParseCommand[Tolka kommando]
    ParseCommand --> ValidateParams[Validera parametrar]
    ValidateParams --> CommandType{Kommandotyp?}
    
    CommandType -->|Process| SetupProcessing[Förbered bearbetning]
    CommandType -->|Query| SetupQuery[Förbered sökning]
    CommandType -->|Generate| SetupGeneration[Förbered generering]
    CommandType -->|Config| SetupConfig[Förbered konfiguration]
    
    SetupProcessing --> ShowProgress[Visa framstegsindikator]
    SetupQuery --> FetchData[Hämta data]
    SetupGeneration --> InitGeneration[Initialisera generering]
    SetupConfig --> LoadConfig[Ladda konfiguration]
    
    ShowProgress --> UpdateTerminal[Uppdatera terminal]
    FetchData --> FormatOutput[Formatera utdata]
    InitGeneration --> GenerateContent[Generera innehåll]
    LoadConfig --> SaveUpdates[Spara uppdateringar]
    
    UpdateTerminal --> WaitForCompletion[Vänta på slutförande]
    FormatOutput --> DisplayResults[Visa resultat]
    GenerateContent --> SaveAndShow[Spara och visa]
    SaveUpdates --> ConfirmChanges[Bekräfta ändringar]
    
    WaitForCompletion --> End([Klar])
    DisplayResults --> End
    SaveAndShow --> End
    ConfirmChanges --> End
```
