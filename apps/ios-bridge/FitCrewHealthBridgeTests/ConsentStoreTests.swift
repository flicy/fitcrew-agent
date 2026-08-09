import Foundation
import Testing
@testable import FitCrewHealthBridge

@Test func configurationRoundTripsWithoutDeviceSecret() throws {
    let suite = "fitcrew-health-bridge-tests-\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defaults.removePersistentDomain(forName: suite)
    let store = ConsentStore(defaults: defaults)
    let configuration = BridgeConfiguration(
        baseURL: URL(string: "https://owner.example")!,
        deviceBindingID: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        consentIDs: [
            "blood_glucose": UUID(
                uuidString: "33333333-3333-4333-8333-333333333333"
            )!,
        ]
    )

    store.configuration = configuration

    #expect(store.configuration == configuration)
}

@Test func replacingDeviceConfigurationClearsPreviousUserSyncState() throws {
    let suite = "fitcrew-health-bridge-tests-\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defaults.removePersistentDomain(forName: suite)
    let store = ConsentStore(defaults: defaults)
    let first = BridgeConfiguration(
        baseURL: URL(string: "https://owner.example")!,
        deviceBindingID: UUID(uuidString: "22222222-2222-4222-8222-222222222222")!,
        consentIDs: [
            "workout": UUID(uuidString: "33333333-3333-4333-8333-333333333333")!,
        ]
    )
    let second = BridgeConfiguration(
        baseURL: URL(string: "https://owner.example")!,
        deviceBindingID: UUID(uuidString: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")!,
        consentIDs: [
            "workout": UUID(uuidString: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")!,
        ]
    )
    store.replaceConfiguration(first, startedAt: Date(timeIntervalSince1970: 100))
    store.lastSync = Date(timeIntervalSince1970: 200)
    store.lastFullReconciliation = Date(timeIntervalSince1970: 300)

    store.replaceConfiguration(second, startedAt: Date(timeIntervalSince1970: 400))

    #expect(store.configuration == second)
    #expect(store.lastSync == nil)
    #expect(store.lastFullReconciliation == nil)
    #expect(store.studyStart == Date(timeIntervalSince1970: 400))
}
