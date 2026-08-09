import SwiftUI

@main
struct FitCrewHealthBridgeApp: App {
    @StateObject private var model = BridgeViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView(model: model)
                .task {
                    BackgroundSyncScheduler.shared.register(model: model)
                    BackgroundSyncScheduler.shared.schedule()
                }
                .onOpenURL { url in
                    Task { await model.configure(from: url) }
                }
        }
    }
}
