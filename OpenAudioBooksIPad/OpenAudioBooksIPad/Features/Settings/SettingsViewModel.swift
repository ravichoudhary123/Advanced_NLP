import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var settings: AppSettings
    @Published var engines: [TextToSpeechEngine] = []

    let ttsEngineManager: TTSEngineManager
    private let settingsRepository: SettingsRepository

    init(settingsRepository: SettingsRepository, ttsEngineManager: TTSEngineManager) {
        self.settingsRepository = settingsRepository
        self.ttsEngineManager = ttsEngineManager
        self.settings = (try? settingsRepository.load()) ?? AppSettings()
        self.engines = ttsEngineManager.engines
    }

    var selectedVoice: VoiceProfile {
        ttsEngineManager.selectedEngine.availableVoices.first(where: { $0.id == settings.selectedVoiceID })
        ?? ttsEngineManager.selectedEngine.availableVoices.first!
    }

    func save() {
        ttsEngineManager.selectedEngineID = settings.selectedEngineID
        try? settingsRepository.save(settings)
    }
}
