import Foundation

@MainActor
final class TTSEngineManager: ObservableObject {
    @Published private(set) var engines: [TextToSpeechEngine]
    @Published var selectedEngineID: String

    init(defaultEngine: TextToSpeechEngine, additionalEngines: [TextToSpeechEngine] = [LocalHTTPPiperAdapter()]) {
        self.engines = [defaultEngine] + additionalEngines
        self.selectedEngineID = defaultEngine.id
    }

    var selectedEngine: TextToSpeechEngine {
        engines.first(where: { $0.id == selectedEngineID }) ?? engines[0]
    }
}
