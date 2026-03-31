import SwiftUI
import SwiftData

private struct DependencyContainerKey: EnvironmentKey {
    static let defaultValue: DependencyContainer = DependencyContainer.preview
}

extension EnvironmentValues {
    var container: DependencyContainer {
        get { self[DependencyContainerKey.self] }
        set { self[DependencyContainerKey.self] = newValue }
    }
}

extension DependencyContainer {
    static let preview: DependencyContainer = {
        let schema = Schema([Audiobook.self, Chapter.self, AudioSegment.self, PlaybackState.self, AppSettings.self])
        let modelContainer = try! ModelContainer(for: schema, configurations: [ModelConfiguration(schema: schema, isStoredInMemoryOnly: true)])
        let context = modelContainer.mainContext
        let repo = SwiftDataAudiobookRepository(context: context)
        let settings = SwiftDataSettingsRepository(context: context)
        let importService = DefaultImportService(parser: DefaultTextParser())
        let manager = TTSEngineManager(defaultEngine: MockTTSEngine())
        let queue = TTSQueueService(repository: repo, engineManager: manager)
        let playback = DefaultPlaybackService(repository: repo)
        return DependencyContainer(audiobookRepository: repo, settingsRepository: settings, importService: importService, ttsEngineManager: manager, ttsQueueService: queue, playbackService: playback)
    }()
}
