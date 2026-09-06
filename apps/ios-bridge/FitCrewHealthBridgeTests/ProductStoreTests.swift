import Foundation
import Testing
@testable import FitCrewHealthBridge

@MainActor
private final class ProductHarness {
    var revision = UUID()
    var binding = UUID()
    var delayed: CheckedContinuation<(Data, URLResponse), Error>?
    var delayNext = true
    let directory = FileManager.default.temporaryDirectory.appending(path: "FitCrew-tests-\(UUID().uuidString)")
    var configuration: BridgeConfiguration { BridgeConfiguration(baseURL: URL(string: "https://example.invalid")!, deviceBindingID: binding, consentIDs: [:]) }
    func response(_ json: String, status: Int = 200) -> (Data, URLResponse) {
        (Data(json.utf8), HTTPURLResponse(url: configuration.baseURL, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
    func transport(_ request: URLRequest) async throws -> (Data, URLResponse) {
        if delayNext {
            delayNext = false
            return try await withCheckedThrowingContinuation { delayed = $0 }
        }
        if request.url!.path == "/v3/capabilities" {
            return response(#"{"ai_available":false,"ai_provider":"none","ai_notice":"none","ai_notice_version":"v1","ai_consent_granted":false}"#)
        }
        return response(#"{"journey":null,"experiments":[],"logs":[],"mission":null,"health":{"sample_count":12,"last_sync_at":null},"privacy_version":"2026-09-07"}"#)
    }
    func makeStore() throws -> ProductStore {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return ProductStore(revisionProvider: { self.revision }, configurationProvider: { self.configuration }, tokenProvider: { "synthetic" }, exportDirectory: directory, transport: { try await self.transport($0) })
    }
    func switchIdentity() { revision = UUID(); binding = UUID() }
    func awaitRequest() async throws {
        for _ in 0..<1000 { if delayed != nil { return }; await Task.yield() }
        throw URLError(.timedOut)
    }
}

@Test @MainActor func oldUnauthorizedResponseCannotClearNewAccount() async throws {
    let harness = ProductHarness()
    let store = try harness.makeStore()
    defer { try? FileManager.default.removeItem(at: harness.directory) }
    let old = Task { await store.refresh() }
    try await harness.awaitRequest()
    harness.switchIdentity()
    store.synchronizeIdentity()
    await store.refresh()
    #expect(store.state?.health.sampleCount == 12)
    harness.delayed?.resume(returning: harness.response("{}", status: 401))
    await old.value
    #expect(store.state?.health.sampleCount == 12)
    #expect(!store.requiresReauthentication)
    #expect(!store.busy)
    #expect(store.error == nil)
}

@Test @MainActor func delayedExportCannotCreateFileForNewAccount() async throws {
    let harness = ProductHarness()
    let store = try harness.makeStore()
    defer { try? FileManager.default.removeItem(at: harness.directory) }
    let old = Task { await store.exportData() }
    try await harness.awaitRequest()
    harness.switchIdentity()
    store.synchronizeIdentity()
    harness.delayed?.resume(returning: harness.response("{}"))
    await old.value
    #expect(store.exportURL == nil)
    #expect(try FileManager.default.contentsOfDirectory(atPath: harness.directory.path).isEmpty)
}

@Test @MainActor func staleMutationCannotAcknowledgeSaveOrEndNewRefresh() async throws {
    let harness = ProductHarness()
    let store = try harness.makeStore()
    defer { try? FileManager.default.removeItem(at: harness.directory) }
    let mutation = Task { await store.mutate("/v3/logs", body: ["note": "synthetic"]) }
    try await harness.awaitRequest()
    let oldResponse = try #require(harness.delayed)
    harness.delayed = nil
    harness.delayNext = true
    harness.switchIdentity()
    store.synchronizeIdentity()
    let refresh = Task { await store.refresh() }
    try await harness.awaitRequest()
    oldResponse.resume(returning: harness.response("{}"))
    #expect(await mutation.value == false)
    #expect(store.busy)
    #expect(store.state == nil)
    harness.delayed?.resume(returning: harness.response(#"{"journey":null,"experiments":[],"logs":[],"mission":null,"health":{"sample_count":9,"last_sync_at":null},"privacy_version":"2026-09-07"}"#))
    await refresh.value
    #expect(store.state?.health.sampleCount == 9)
    #expect(!store.busy)
}

@Test @MainActor func supersededAndOrphanExportsAreRemovedOnIdentityChange() async throws {
    let harness = ProductHarness()
    harness.delayNext = false
    let store = try harness.makeStore()
    defer { try? FileManager.default.removeItem(at: harness.directory) }
    let unrelated = harness.directory.appending(path: "unrelated.json")
    try Data("keep".utf8).write(to: unrelated)
    await store.exportData()
    let first = try #require(store.exportURL)
    await store.exportData()
    #expect(!FileManager.default.fileExists(atPath: first.path))
    try Data("old".utf8).write(to: harness.directory.appending(path: "FitCrew-export-orphan.json"))
    harness.switchIdentity()
    store.synchronizeIdentity()
    #expect(store.exportURL == nil)
    #expect(try FileManager.default.contentsOfDirectory(atPath: harness.directory.path) == ["unrelated.json"])
}

@Test func reauthenticationRotatesRevisionEvenForSameBinding() throws {
    let suite = "fitcrew-epoch-test-\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defer { defaults.removePersistentDomain(forName: suite) }
    let consent = ConsentStore(defaults: defaults)
    let configuration = BridgeConfiguration(baseURL: URL(string: "https://example.invalid")!, deviceBindingID: UUID(), consentIDs: [:])
    consent.replaceConfiguration(configuration)
    let first = consent.identityRevision
    consent.replaceConfiguration(configuration)
    #expect(consent.identityRevision != first)
}

@Test func publicPolicyRequiresConfiguredHTTPSURL() {
    #expect(ReleaseConfiguration.httpsURL(nil) == nil)
    #expect(ReleaseConfiguration.httpsURL("http://example.invalid/privacy") == nil)
    #expect(ReleaseConfiguration.httpsURL("https://secret@example.invalid/privacy") == nil)
    #expect(ReleaseConfiguration.httpsURL("https://example.invalid/privacy") != nil)
}

@Test func identitySnapshotRejectsPairingAndSameBindingReauthentication() throws {
    let suite = "fitcrew-snapshot-\(UUID().uuidString)"
    let defaults = try #require(UserDefaults(suiteName: suite))
    defer { defaults.removePersistentDomain(forName: suite) }
    let store = ConsentStore(defaults: defaults)
    let loginStart = AccountIdentitySnapshot(store: store)
    let configuration = BridgeConfiguration(baseURL: URL(string: "https://example.invalid")!, deviceBindingID: UUID(), consentIDs: [:])
    store.replaceConfiguration(configuration)
    #expect(!loginStart.isCurrent(in: store))
    let healthStart = AccountIdentitySnapshot(store: store)
    #expect(healthStart.isCurrent(in: store))
    store.replaceConfiguration(configuration)
    #expect(!healthStart.isCurrent(in: store))
    let nextStart = AccountIdentitySnapshot(store: store)
    store.configuration = BridgeConfiguration(baseURL: URL(string: "https://other.invalid")!, deviceBindingID: UUID(), consentIDs: [:])
    #expect(!nextStart.isCurrent(in: store))
}
