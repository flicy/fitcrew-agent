import SwiftUI

struct ContentView: View {
    @ObservedObject var model: BridgeViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section("连接状态") {
                    LabeledContent("HealthKit", value: model.authorizationStatus)
                    LabeledContent("上次同步", value: model.lastSyncText)
                    LabeledContent("状态", value: model.statusMessage)
                }
                Section("授权与同步") {
                    Button("授权 Apple 健康") {
                        Task { await model.requestAuthorization() }
                    }
                    Button("立即增量同步") {
                        Task { await model.sync(fullReconciliation: false) }
                    }
                    .disabled(!model.isConfigured)
                    Button("执行全量对账") {
                        Task { await model.sync(fullReconciliation: true) }
                    }
                    .disabled(!model.isConfigured)
                }
                Section("隐私边界") {
                    Text("原始数据只加密上传到你的 Owner-only 环境；群聊和模型都不能读取原始健康时间序列。")
                        .font(.footnote)
                    Link(
                        "隐私政策 / Privacy Policy",
                        destination: URL(
                            string: "https://github.com/flicy/fitcrew-agent/blob/main/docs/privacy/data-processing-and-retention.md"
                        )!
                    )
                }
            }
            .navigationTitle("FitCrew Health Bridge")
        }
    }
}
