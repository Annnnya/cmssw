import FWCore.ParameterSet.Config as cms

process = cms.Process("UnsplitTestProcess")

process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(0),
    output = cms.optional.untracked.allowed(cms.int32,cms.PSet)
)

process.maxLuminosityBlocks = cms.untracked.PSet(
    input = cms.untracked.int32(-1)
)

process.options = cms.untracked.PSet(
    IgnoreCompletely = cms.untracked.vstring(),
    Rethrow = cms.untracked.vstring(),
    TryToContinue = cms.untracked.vstring(),
    accelerators = cms.untracked.vstring('*'),
    allowUnscheduled = cms.obsolete.untracked.bool,
    canDeleteEarly = cms.untracked.vstring(),
    deleteNonConsumedUnscheduledModules = cms.untracked.bool(True),
    dumpOptions = cms.untracked.bool(False),
    emptyRunLumiMode = cms.obsolete.untracked.string,
    eventSetup = cms.untracked.PSet(
        forceNumberOfConcurrentIOVs = cms.untracked.PSet(
            allowAnyLabel_=cms.required.untracked.uint32
        ),
        numberOfConcurrentIOVs = cms.untracked.uint32(0)
    ),
    fileMode = cms.untracked.string('FULLMERGE'),
    forceEventSetupCacheClearOnNewRun = cms.untracked.bool(False),
    holdsReferencesToDeleteEarly = cms.untracked.VPSet(),
    makeTriggerResults = cms.obsolete.untracked.bool,
    modulesToCallForTryToContinue = cms.untracked.vstring(),
    modulesToIgnoreForDeleteEarly = cms.untracked.vstring(),
    numberOfConcurrentLuminosityBlocks = cms.untracked.uint32(1),
    numberOfConcurrentRuns = cms.untracked.uint32(1),
    numberOfStreams = cms.untracked.uint32(1),
    numberOfThreads = cms.untracked.uint32(1),
    printDependencies = cms.untracked.bool(False),
    sizeOfStackForThreadsInKB = cms.optional.untracked.uint32,
    throwIfIllegalParameter = cms.untracked.bool(True),
    wantSummary = cms.untracked.bool(False)
)

process.fedRawDataCollectionProducer = cms.EDProducer("TestWriteFEDRawDataCollection",
    FEDData0 = cms.vuint32(
        0, 1, 2, 3, 4,
        5, 6, 7
    ),
    FEDData3 = cms.vuint32(
        100, 101, 102, 103, 104,
        105, 106, 107
    )
)


process.rawDataBufferProducer = cms.EDProducer("TestWriteRawDataBuffer",
    dataPattern1 = cms.vuint32(
        0, 1, 2, 3, 4,
        5, 6, 7, 8, 9,
        10, 11, 12, 13, 14,
        15
    ),
    dataPattern2 = cms.vuint32(
        100, 101, 102, 103, 104,
        105, 106, 107, 108, 109,
        110, 111, 112, 113, 114,
        115
    )
)


process.triggerEventProducer = cms.EDProducer("TestWriteTriggerEvent",
    collectionKeys = cms.vuint32(11, 21, 31),
    collectionTags = cms.vstring(
        'moduleA',
        'moduleB',
        'moduleC'
    ),
    elementsPerVector = cms.uint32(2),
    etas = cms.vdouble(101.0, 102.0, 103.0),
    filterIds = cms.vint32(1001, 1002, 1003, 1004),
    filterKeys = cms.vuint32(2001, 2002, 2003, 2004),
    filterTags = cms.vstring(
        'moduleAA',
        'moduleBB'
    ),
    ids = cms.vint32(1, 3, 5),
    masses = cms.vdouble(301.0, 302.0, 303.0),
    phis = cms.vdouble(201.0, 202.0, 203.0),
    pts = cms.vdouble(11.0, 21.0, 31.0),
    usedProcessName = cms.string('testName')
)


process.triggerResultsProducer = cms.EDProducer("TestWriteTriggerResults",
    hltStates = cms.vuint32(0, 1, 2, 3),
    moduleIndexes = cms.vuint32(11, 21, 31, 41),
    names = cms.vstring(),
    parameterSetID = cms.string('8b99d66b6c3865c75e460791f721202d')
)


process.PrintNames = cms.EDAnalyzer("DumpProductNames",
    mightGet = cms.optional.untracked.vstring,
    outputFile = cms.string('.cppnamedir/print_cppnames.json')
)


process.testReadFEDRawDataCollection = cms.EDAnalyzer("TestReadFEDRawDataCollection",
    expectedFEDData0 = cms.vuint32(
        0, 1, 2, 3, 4,
        5, 6, 7
    ),
    expectedFEDData3 = cms.vuint32(
        100, 101, 102, 103, 104,
        105, 106, 107
    ),
    fedRawDataCollectionTag = cms.InputTag("fedRawDataCollectionProducer")
)


process.testReadRawDataBuffer = cms.EDAnalyzer("TestReadRawDataBuffer",
    dataPattern1 = cms.vuint32(
        0, 1, 2, 3, 4,
        5, 6, 7, 8, 9,
        10, 11, 12, 13, 14,
        15
    ),
    dataPattern2 = cms.vuint32(
        100, 101, 102, 103, 104,
        105, 106, 107, 108, 109,
        110, 111, 112, 113, 114,
        115
    ),
    rawDataBufferTag = cms.InputTag("rawDataBufferProducer")
)


process.testReadTriggerEvent = cms.EDAnalyzer("TestReadTriggerEvent",
    expectedCollectionKeys = cms.vuint32(11, 21, 31),
    expectedCollectionTags = cms.vstring(
        'moduleA',
        'moduleB',
        'moduleC'
    ),
    expectedElementsPerVector = cms.uint32(2),
    expectedEtas = cms.vdouble(101.0, 102.0, 103.0),
    expectedFilterIds = cms.vint32(1001, 1002, 1003, 1004),
    expectedFilterKeys = cms.vuint32(2001, 2002, 2003, 2004),
    expectedFilterTags = cms.vstring(
        'moduleAA',
        'moduleBB'
    ),
    expectedIds = cms.vint32(1, 3, 5),
    expectedMasses = cms.vdouble(301.0, 302.0, 303.0),
    expectedPhis = cms.vdouble(201.0, 202.0, 203.0),
    expectedPts = cms.vdouble(11.0, 21.0, 31.0),
    expectedUsedProcessName = cms.string('testName'),
    triggerEventTag = cms.InputTag("triggerEventProducer")
)


process.testReadTriggerResults = cms.EDAnalyzer("TestReadTriggerResults",
    expectedHLTStates = cms.vuint32(0, 1, 2, 3),
    expectedModuleIndexes = cms.vuint32(11, 21, 31, 41),
    expectedNames = cms.vstring(),
    expectedParameterSetID = cms.string('8b99d66b6c3865c75e460791f721202d'),
    triggerResultsTag = cms.InputTag("triggerResultsProducer")
)


process.MessageLogger = cms.Service("MessageLogger",
    cerr = cms.untracked.PSet(
        FwkReport = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000),
            reportEvery = cms.untracked.int32(1)
        ),
        FwkSummary = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000),
            reportEvery = cms.untracked.int32(1)
        ),
        INFO = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000)
        ),
        Root_NoDictionary = cms.untracked.PSet(
            limit = cms.untracked.int32(0)
        ),
        default = cms.untracked.PSet(
            limit = cms.untracked.int32(10000000)
        ),
        enable = cms.untracked.bool(True),
        enableStatistics = cms.untracked.bool(False),
        lineLength = cms.optional.untracked.int32,
        noLineBreaks = cms.optional.untracked.bool,
        noTimeStamps = cms.untracked.bool(False),
        resetStatistics = cms.untracked.bool(False),
        statisticsThreshold = cms.untracked.string('WARNING'),
        threshold = cms.untracked.string('INFO'),
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    cout = cms.untracked.PSet(
        enable = cms.untracked.bool(False),
        enableStatistics = cms.untracked.bool(False),
        lineLength = cms.optional.untracked.int32,
        noLineBreaks = cms.optional.untracked.bool,
        noTimeStamps = cms.optional.untracked.bool,
        resetStatistics = cms.untracked.bool(False),
        statisticsThreshold = cms.optional.untracked.string,
        threshold = cms.optional.untracked.string,
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    debugModules = cms.untracked.vstring(),
    default = cms.untracked.PSet(
        limit = cms.optional.untracked.int32,
        lineLength = cms.untracked.int32(80),
        noLineBreaks = cms.untracked.bool(False),
        noTimeStamps = cms.untracked.bool(False),
        reportEvery = cms.untracked.int32(1),
        statisticsThreshold = cms.untracked.string('INFO'),
        threshold = cms.untracked.string('INFO'),
        timespan = cms.optional.untracked.int32,
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            limit = cms.optional.untracked.int32,
            reportEvery = cms.untracked.int32(1),
            timespan = cms.optional.untracked.int32
        )
    ),
    files = cms.untracked.PSet(
        allowAnyLabel_=cms.optional.untracked.PSetTemplate(
            enableStatistics = cms.untracked.bool(False),
            extension = cms.optional.untracked.string,
            filename = cms.optional.untracked.string,
            lineLength = cms.optional.untracked.int32,
            noLineBreaks = cms.optional.untracked.bool,
            noTimeStamps = cms.optional.untracked.bool,
            output = cms.optional.untracked.string,
            resetStatistics = cms.untracked.bool(False),
            statisticsThreshold = cms.optional.untracked.string,
            threshold = cms.optional.untracked.string,
            allowAnyLabel_=cms.optional.untracked.PSetTemplate(
                limit = cms.optional.untracked.int32,
                reportEvery = cms.untracked.int32(1),
                timespan = cms.optional.untracked.int32
            )
        )
    ),
    suppressDebug = cms.untracked.vstring(),
    suppressFwkInfo = cms.untracked.vstring(),
    suppressInfo = cms.untracked.vstring(),
    suppressWarning = cms.untracked.vstring(),
    allowAnyLabel_=cms.optional.untracked.PSetTemplate(
        limit = cms.optional.untracked.int32,
        reportEvery = cms.untracked.int32(1),
        timespan = cms.optional.untracked.int32
    )
)


process.path1 = cms.Path(process.fedRawDataCollectionProducer+process.testReadFEDRawDataCollection)


process.path2 = cms.Path(process.rawDataBufferProducer+process.testReadRawDataBuffer)


process.path3 = cms.Path(process.triggerEventProducer+process.testReadTriggerEvent)


process.path4 = cms.Path(process.triggerResultsProducer+process.testReadTriggerResults)


process.PrintNamesPath = cms.EndPath(process.PrintNames)


process.schedule = cms.Schedule(*[ process.path1, process.path2, process.path3, process.path4, process.PrintNamesPath ])
