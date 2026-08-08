import FitCrewHealthCore
import Foundation

struct SyncClient {
    let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func upload(
        _ batch: HealthSyncBatchDTO,
        to baseURL: URL,
        deviceToken: String
    ) async throws {
        var request = URLRequest(url: baseURL.appending(path: "/v1/health/sync"))
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder.fitCrew.encode(batch)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(deviceToken)", forHTTPHeaderField: "Authorization")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw URLError(.badServerResponse)
        }
    }
}

@MainActor
final class BridgeViewModel: ObservableObject {
    @Published private(set) var statusMessage = "等待授权"
    @Published private(set) var authorizationStatus = "未确认"
    @Published private(set) var lastSync: Date?

    private let healthKit = HealthKitClient()
    private let syncClient = SyncClient()
    private let consentStore = ConsentStore()

    init() {
        lastSync = consentStore.lastSync
    }

    var isConfigured: Bool {
        consentStore.configuration != nil && KeychainStore.deviceToken() != nil
    }

    var lastSyncText: String {
        guard let lastSync else { return "尚未同步" }
        return lastSync.formatted(date: .abbreviated, time: .shortened)
    }

    func configure(from url: URL) {
        do {
            let pairing = try PairingDecoder.decode(url)
            try KeychainStore.saveDeviceToken(pairing.deviceToken)
            consentStore.replaceConfiguration(BridgeConfiguration(
                baseURL: pairing.baseURL,
                deviceBindingID: pairing.deviceBindingID,
                consentIDs: pairing.consentIDs
            ))
            lastSync = consentStore.lastSync
            statusMessage = "设备绑定成功，请授权 Apple 健康"
        } catch {
            statusMessage = "设备绑定失败：\(error.localizedDescription)"
        }
    }

    func requestAuthorization() async {
        do {
            try await healthKit.requestAuthorization()
            authorizationStatus = "已请求最小读取权限"
            statusMessage = "授权完成后可以同步"
        } catch {
            statusMessage = "授权失败：\(error.localizedDescription)"
        }
    }

    @discardableResult
    func sync(fullReconciliation: Bool) async -> Bool {
        guard let configuration = consentStore.configuration,
              let token = KeychainStore.deviceToken()
        else {
            statusMessage = "请先完成设备绑定"
            return false
        }
        let endDate = Date()
        let startDate = fullReconciliation
            ? Calendar.current.date(byAdding: .day, value: -30, to: endDate)!
            : (lastSync ?? Calendar.current.date(byAdding: .day, value: -1, to: endDate)!)
        do {
            let samples = try await healthKit.readSamples(since: startDate, until: endDate)
            let batches = try BatchPlanner.makeBatches(
                deviceBindingID: configuration.deviceBindingID,
                consentIDs: configuration.consentIDs,
                cursor: startDate.ISO8601Format(),
                source: "apple-healthkit",
                timezone: TimeZone.current.identifier,
                sentAt: endDate,
                fullReconciliation: fullReconciliation,
                samples: samples
            )
            for batch in batches {
                try await syncClient.upload(batch, to: configuration.baseURL, deviceToken: token)
            }
            lastSync = endDate
            consentStore.lastSync = endDate
            if fullReconciliation {
                consentStore.lastFullReconciliation = endDate
            }
            statusMessage = "同步成功，共处理 \(samples.count) 条样本"
            BackgroundSyncScheduler.shared.schedule()
            return true
        } catch {
            statusMessage = "同步失败，游标未推进：\(error.localizedDescription)"
            return false
        }
    }

    var requiresFullReconciliation: Bool {
        guard let studyStart = consentStore.studyStart else { return false }
        return StudySchedule.requiresFullReconciliation(
            startedAt: studyStart,
            lastFullReconciliation: consentStore.lastFullReconciliation,
            now: Date()
        )
    }
}
