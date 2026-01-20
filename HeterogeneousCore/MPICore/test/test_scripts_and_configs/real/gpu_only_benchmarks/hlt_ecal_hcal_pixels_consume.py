import FWCore.ParameterSet.Config as cms
import os

from HLTrigger.Configuration.common import *

import sys
sys.path.insert(0, '..')

from hlt import process as _process

process = cms.Process("REMOTE")

process.load("Configuration.StandardSequences.Accelerators_cff")
# process.load("FWCore.MessageLogger.MessageLogger_cfi")

# load the event setup
for module in _process.psets.keys():
    setattr(process, module, getattr(_process, module).clone())
for module in _process.es_sources.keys():
    setattr(process, module, getattr(_process, module).clone())
for module in _process.es_producers.keys():
    setattr(process, module, getattr(_process, module).clone())


process.options.numberOfThreads = int(os.environ.get("EXPERIMENT_THREADS", 32))
process.options.numberOfStreams = int(os.environ.get("EXPERIMENT_STREAMS", 24))
process.options.numberOfConcurrentLuminosityBlocks = 1


# FastTimer output
# experiment_name = os.environ.get("EXPERIMENT_NAME", "unnamed")
# output_dir = os.environ.get("EXPERIMENT_OUTPUT_DIR", "../../test_results/one_time_tests/")

# process.FastTimerService.writeJSONSummary = True
# process.FastTimerService.jsonFileName=cms.untracked.string(f"{output_dir}/local_{experiment_name}.json")

# process.FastTimerService = _process.FastTimerService.clone()
# process.FastTimerService.writeJSONSummary = True
# process.FastTimerService.jsonFileName=cms.untracked.string(f"../../../test_results/results_consume.json")

process.ThroughputService = cms.Service('ThroughputService',
    enableDQM = cms.untracked.bool(False),
    printEventSummary = cms.untracked.bool(True),
    eventResolution = cms.untracked.uint32(10),
    eventRange = cms.untracked.uint32(10300),
)

process.MessageLogger.cerr.ThroughputService = cms.untracked.PSet(
    limit = cms.untracked.int32(10000000),
    reportEvery = cms.untracked.int32(1)
)


process.hltGetRaw = cms.EDAnalyzer( "HLTGetRaw",
    RawDataCollection = cms.InputTag( "rawDataCollector" )
)
process.hltPSetMap = cms.EDProducer( "ParameterSetBlobProducer" )
process.hltBoolFalse = cms.EDFilter( "HLTBool",
    result = cms.bool( False )
)
process.hltBackend = cms.EDProducer( "AlpakaBackendProducer@alpaka"
)
process.hltStatusOnGPUFilter = cms.EDFilter( "AlpakaBackendFilter",
    producer = cms.InputTag( 'hltBackend','backend' ),
    backends = cms.vstring( 'CudaAsync',
      'ROCmAsync' )
)

process.HLTriggerFirstPath = cms.Path( process.hltGetRaw + process.hltPSetMap + process.hltBoolFalse )
process.Status_OnCPU = cms.Path( process.hltBackend + ~process.hltStatusOnGPUFilter )
process.Status_OnGPU = cms.Path( process.hltBackend + process.hltStatusOnGPUFilter )

process.DQMStore = _process.DQMStore.clone()
process.EvFDaqDirector = _process.EvFDaqDirector.clone()
process.source = _process.source.clone()
process.maxEvents.input = 1000

# HBHE local reconstruction from the HLT menu
process.hltHcalDigis = _process.hltHcalDigis.clone()
process.hltHcalDigisSoA = _process.hltHcalDigisSoA.clone()
process.hltHbheRecoSoA = _process.hltHbheRecoSoA.clone()

process.hltParticleFlowRecHitHBHESoA = _process.hltParticleFlowRecHitHBHESoA.clone()
process.hltParticleFlowClusterHBHESoA = _process.hltParticleFlowClusterHBHESoA.clone()

process.dummyHcalConsume1 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltHbheRecoSoA" )
)

process.dummyHcalConsume2 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltParticleFlowRecHitHBHESoA" )
)

process.dummyHcalConsume3 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltParticleFlowClusterHBHESoA" )
)


# run the HBHE local reconstruction
process.HLTLocalHBHE = cms.Path(
    process.hltGetRaw +
    process.hltHcalDigis +
    process.hltHcalDigisSoA +
    process.hltHbheRecoSoA +
    process.hltParticleFlowRecHitHBHESoA +
    process.hltParticleFlowClusterHBHESoA +
    process.dummyHcalConsume1 +
    process.dummyHcalConsume2 +
    process.dummyHcalConsume3
)

# ECAL local reconstruction from the HLT menu
process.hltEcalDigisSoA = _process.hltEcalDigisSoA.clone()
process.hltEcalUncalibRecHitSoA = _process.hltEcalUncalibRecHitSoA.clone()

# to avoid the bug you can either syncronise the module 
# 1) via explicit alpaka parameter 
# 2) or by adding dummy consumer at the end of the ECAL sequence

# process.hltEcalUncalibRecHitSoA.alpaka.synchronize = cms.untracked.bool(True)

process.dummyEcalConsume1 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltEcalDigisSoA" )
)

process.dummyEcalConsume2 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltEcalUncalibRecHitSoA" )
)


# run the ECAL local reconstruction
process.HLTLocalECAL = cms.Path(
    process.hltGetRaw +
    process.hltEcalDigisSoA +
    process.hltEcalUncalibRecHitSoA +
    process.dummyEcalConsume1 +
    process.dummyEcalConsume2
)

# Pixel local reconstruction from the HLT menu
process.hltOnlineBeamSpot = _process.hltOnlineBeamSpot.clone()
process.hltOnlineBeamSpotDevice = _process.hltOnlineBeamSpotDevice.clone()
process.hltSiPixelClustersSoA = _process.hltSiPixelClustersSoA.clone()
process.hltSiPixelRecHitsSoA = _process.hltSiPixelRecHitsSoA.clone()
process.hltPixelTracksSoA = _process.hltPixelTracksSoA.clone()
process.hltPixelVerticesSoA = _process.hltPixelVerticesSoA.clone()

process.dummyPixelConsume1 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltSiPixelClustersSoA" )
)

process.dummyPixelConsume2 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltSiPixelRecHitsSoA" )
)

process.dummyPixelConsume3 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltPixelTracksSoA" )
)

process.dummyPixelConsume4 = cms.EDAnalyzer("GenericConsumer",
    eventProducts = cms.untracked.vstring( "hltPixelVerticesSoA" )
)


process.HLTLocalPixel = cms.Path(
    process.hltGetRaw +
    process.hltOnlineBeamSpot +
    process.hltOnlineBeamSpotDevice +
    process.hltSiPixelClustersSoA +
    process.hltSiPixelRecHitsSoA +
    process.hltPixelTracksSoA +
    process.hltPixelVerticesSoA +
    process.dummyPixelConsume1 +
    process.dummyPixelConsume2 +
    process.dummyPixelConsume3 +
    process.dummyPixelConsume4
)

# schedule the reconstruction
process.schedule = cms.Schedule(
    process.HLTriggerFirstPath,
    process.Status_OnCPU,
    process.Status_OnGPU,
    process.HLTLocalHBHE,
    process.HLTLocalECAL,
    process.HLTLocalPixel
)

# process.Tracer = cms.Service("Tracer")
