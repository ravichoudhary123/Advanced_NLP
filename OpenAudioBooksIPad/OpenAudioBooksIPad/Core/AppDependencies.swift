import Foundation
import SwiftData

@MainActor
final class AppDependencies {
    let modelContainer: ModelContainer
    let container: DependencyContainer

    let libraryViewModel: LibraryViewModel
    let playerViewModel: PlayerViewModel
    let settingsViewModel: SettingsViewModel

    private init(modelContainer: ModelContainer, container: DependencyContainer) {
        self.modelContainer = modelContainer
        self.container = container
        self.libraryViewModel = LibraryViewModel(repository: container.audiobookRepository, queueService: container.ttsQueueService)
        self.playerViewModel = PlayerViewModel(playbackService: container.playbackService, repository: container.audiobookRepository)
        self.settingsViewModel = SettingsViewModel(settingsRepository: container.settingsRepository, ttsEngineManager: container.ttsEngineManager)
    }

    static func makeDefault() -> AppDependencies {
        let schema = Schema([
            Audiobook.self,
            Chapter.self,
            AudioSegment.self,
            PlaybackState.self,
            AppSettings.self
        ])

        let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
        let modelContainer = try! ModelContainer(for: schema, configurations: [configuration])
        let context = modelContainer.mainContext

        let audiobookRepository = SwiftDataAudiobookRepository(context: context)
        let settingsRepository = SwiftDataSettingsRepository(context: context)
        let parser = DefaultTextParser()
        let importService = DefaultImportService(parser: parser)
        let ttsEngineManager = TTSEngineManager(defaultEngine: MockTTSEngine())
        let queue = TTSQueueService(repository: audiobookRepository, engineManager: ttsEngineManager)
        let playback = DefaultPlaybackService(repository: audiobookRepository)

        let container = DependencyContainer(
            audiobookRepository: audiobookRepository,
            settingsRepository: settingsRepository,
            importService: importService,
            ttsEngineManager: ttsEngineManager,
            ttsQueueService: queue,
            playbackService: playback
        )

        return AppDependencies(modelContainer: modelContainer, container: container)
    }

    func bootstrapIfNeeded() async {
        await SampleDataSeeder.seedIfNeeded(repository: container.audiobookRepository)
        await container.ttsQueueService.resumePendingJobs()
    }
}

struct DependencyContainer {
    let audiobookRepository: AudiobookRepository
    let settingsRepository: SettingsRepository
    let importService: ImportService
    let ttsEngineManager: TTSEngineManager
    let ttsQueueService: TTSQueueService
    let playbackService: PlaybackService
}
