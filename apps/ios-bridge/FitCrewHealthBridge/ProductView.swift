import SwiftUI
import FitCrewHealthCore

struct ContentView: View {
    @ObservedObject var model: BridgeViewModel
    @StateObject private var store = ProductStore()
    @State private var tab = 0
    @State private var trendDays = 30
    @State private var selectedTrend: ProductTrendPoint?
    @State private var showLighten = false
    @State private var lightenMission: ProductMission?
    @State private var goal = "sleep"
    @State private var energy = 3
    @State private var stress = 1
    @State private var feeling = "正常"
    @State private var note = ""
    @State private var sleepFeeling = ""
    @State private var trainingFeeling = ""
    @State private var stressSource = ""
    @State private var pairing = ""
    @State private var experiment: ProductExperiment?
    @State private var stoppingExperiment: ProductExperiment?
    @State private var deletion: String?
    @State private var saved = false
    @State private var showHealthConsent = false
    private let green = Color(red: 124/255, green: 58/255, blue: 237/255)
    private let background = Color(red: 245/255, green: 245/255, blue: 250/255)

    var body: some View {
        TabView(selection: $tab) {
            page("今天", "TODAY · 一次做好一件小事") { today }.tabItem { Label("今天", systemImage: "sun.max") }.tag(0)
            page("身体旅程", "JOURNEY · 90 天，慢慢变好") { journey }.tabItem { Label("旅程", systemImage: "leaf") }.tag(1)
            page("我的实验", "EXPERIMENTS · 找到适合自己的方式") { experiments }.tabItem { Label("实验", systemImage: "flask") }.tag(2)
            page("身体记录", "LOG · 留下你真实的感受") { logs }.tabItem { Label("记录", systemImage: "square.and.pencil") }.tag(3)
            page("我的", "PROFILE · 你的数据，由你掌握") { profile }.tabItem { Label("我的", systemImage: "person.crop.circle") }.tag(4)
        }.tint(green)
        .task { if model.isConfigured { await store.refresh() } }
        .sheet(isPresented: $showHealthConsent) { HealthConsentView(model: model) }
        .onChange(of: model.identityRevision) { _, _ in
            store.synchronizeIdentity()
            showLighten = false; lightenMission = nil; selectedTrend = nil
            note = ""; saved = false; experiment = nil; stoppingExperiment = nil; deletion = nil; showHealthConsent = false
            energy = 3; stress = 1; feeling = "正常"
            sleepFeeling = ""; trainingFeeling = ""; stressSource = ""
            if model.isConfigured { Task { await store.refresh() } }
        }
        .onChange(of: store.state?.trends?.points) { _, _ in selectedTrend = nil }
        .sheet(item: $selectedTrend) { point in
            NavigationStack {
                VStack(alignment: .leading, spacing: 20) {
                    if let energy = point.energy, let stress = point.stress {
                        Text("\(point.count) 条手动记录 · 精力均值 \(energy.formatted()) / 5 · 压力均值 \(stress.formatted()) / 3")
                    } else { Text("当天没有记录，不能推断当天状态。") }
                    ForEach(point.events ?? [], id: \.self) { Text($0) }
                    if (point.events ?? []).isEmpty { Text("当天无已记录的实验开始事件。") }
                    Text("实验事件仅作背景，不说明变化的原因。").font(.footnote)
                    Button("关闭") { selectedTrend = nil }
                }.padding(24).navigationTitle(point.date)
            }.presentationDetents([.medium])
        }
        .sheet(isPresented: $showLighten) {
            NavigationStack {
                VStack(alignment: .leading, spacing: 20) {
                    Text("选择后保存；取消会保留原任务。")
                    Button("只记录此刻的感受") { lighten("brief_check") }
                    Button("留一分钟安静休息") { lighten("quiet_minute") }
                    if let error = store.error { Text(error).foregroundStyle(.red) }
                    Button("取消") { showLighten = false }
                }.padding(24).disabled(store.busy).navigationTitle("今天可以轻一点")
            }.presentationDetents([.medium]).interactiveDismissDisabled(store.busy)
        }
        .sheet(item: $experiment) { e in
            NavigationStack {
                ScrollView { VStack(alignment: .leading, spacing: 20) {
                    Text(e.title).font(.largeTitle.bold())
                    details(e)
                    Text("\(sourceLabel(e))。这是生活方式建议，不是医疗建议。你可以暂停或停止；样本不足时，可能无法得出结论。")
                    Button("我已了解并同意开始") { Task { if await transition(e, "accept") { experiment = nil } } }.buttonStyle(.borderedProminent).disabled(store.busy)
                    if let error = store.error { Text(error).foregroundStyle(.red) }
                }.padding(24) }.toolbar { Button("关闭") { experiment = nil } }
            }.presentationDragIndicator(.visible)
        }
        .confirmationDialog("停止这次实验？", isPresented: Binding(get: { stoppingExperiment != nil }, set: { if !$0 { stoppingExperiment = nil } }), titleVisibility: .visible) {
            Button("停止实验", role: .destructive) {
                if let value = stoppingExperiment { Task { await transition(value, "stop") } }
                stoppingExperiment = nil
            }
        } message: { Text("保留已有记录和实验历史，不再继续观察。") }
        .confirmationDialog("永久删除？此操作无法撤销。", isPresented: Binding(get: { deletion != nil }, set: { if !$0 { deletion = nil } }), titleVisibility: .visible) {
            Button("确认永久删除", role: .destructive) {
                if let value = deletion { Task { if value.hasPrefix("logs/") { await store.mutate("/v3/\(value)", method: "DELETE") } else if await store.delete(value) { model.refreshSyncState() } } }; deletion = nil
            }
        }
    }

    private func page<C: View>(_ title: String, _ subtitle: String, @ViewBuilder content: () -> C) -> some View {
        NavigationStack { ScrollView { VStack(alignment: .leading, spacing: 20) {
            Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            if !model.isConfigured { card { Text("还未连接账号").font(.headline); Text("连接后即可保存旅程、实验和身体记录。Apple 健康授权是可选的。"); Button("前往连接") { tab = 4 }.frame(minHeight: 44) } }
            if let error = store.error { card { Text(error).foregroundStyle(.red); Button("重新加载") { Task { await store.refresh() } }.frame(minHeight: 44) } }
            if store.busy { ProgressView("正在处理…").frame(maxWidth: .infinity) }
            content()
        }.padding(20) }.background(background).navigationTitle(title).refreshable { if model.isConfigured { await store.refresh() } } }
    }
    private func card<C: View>(accent: Bool = false, @ViewBuilder content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 14, content: content).frame(maxWidth: .infinity, alignment: .leading).padding(22)
            .foregroundStyle(accent ? Color.white : Color.primary)
            .tint(accent ? .white : green)
            .background(accent ? green : Color(uiColor: .secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 26))
            .shadow(color: green.opacity(accent ? 0.16 : 0.035), radius: 12, y: 5)
    }
    private var today: some View {
        Group {
            if let progress = store.state?.onboarding, progress.step < 7 { onboardingCard(progress) }
            if let context = store.state?.todayContext { card {
                Text(context.title).font(.title2.bold())
                Text(context.detail)
                Text("来源：\(context.source) · \(context.windowStart) — \(context.windowEnd)").font(.footnote)
                Button("查看数据用途与授权") { tab = 4 }
            } }
            card(accent: true) {
                Label("最近一次记录", systemImage: "leaf").font(.headline)
                Text(store.state?.logs.last?.feeling ?? "先听听身体的声音").font(.largeTitle.bold())
                if let log = store.state?.logs.last { Text("最近记录 · 精力 \(log.energy)/5 · 压力 \(log.stress)/3") } else { Text("今天感觉怎么样？留下你的第一条记录。") }
                Button("做一次 Body Check") { tab = 3 }.frame(minHeight: 44)
            }
            if let mission = store.state?.mission {
                card {
                    Text("今天的一小步").font(.headline); Text(mission.title).font(.title.bold()); Text(mission.why).foregroundStyle(.secondary); Text("状态：\(status(mission.status))")
                    if let adjustedAt = mission.adjustedAt { Text("调整已保存：\(adjustedAt) · 版本 \(mission.revision)").font(.footnote) }
                    if ["proposed", "pending", "accepted", "lightened"].contains(mission.status) {
                        Button("我做到了") { Task { await store.mutate("/v3/mission", body: ["action": "done", "mission_id": mission.id, "revision": mission.revision]) } }.buttonStyle(.borderedProminent)
                        HStack { Button("轻一点") { lightenMission = mission; showLighten = true }; Spacer(); Button("今天跳过") { Task { await store.mutate("/v3/mission", body: ["action": "skip", "mission_id": mission.id, "revision": mission.revision]) } } }.frame(minHeight: 44)
                    }
                }.disabled(store.busy)
            } else { card { Text("从一个方向开始").font(.title2.bold()); Text("选择你的 90 天目标，开启今天的小行动。"); Button("选择旅程") { tab = 1 }.frame(minHeight: 44) } }
            if let active = store.state?.experiments.first(where: { $0.status == "running" }) { card { Text("正在验证").font(.headline); Text(active.title).font(.title2.bold()); Text(active.intervention); Button("查看实验与下一次检查") { tab = 2 }.frame(minHeight: 44) } }
            if let next = store.state?.nextCheck { card {
                Text("下一次检查：\(next.title)").font(.headline)
                Text(next.detail)
                Button(next.action == "log" ? "记录此刻感受" : next.action == "journey" ? "选择旅程" : "查看实验") {
                    tab = next.action == "log" ? 3 : next.action == "journey" ? 1 : 2
                }.frame(minHeight: 44)
            } }
            card { Text("Apple 健康").font(.headline); Text(store.state?.health.sampleCount ?? 0 == 0 ? "暂无同步数据" : "已同步 \(store.state!.health.sampleCount) 条样本"); Text("只展示实际同步状态；未授权或没有样本时，不推测身体指标。").font(.footnote).foregroundStyle(.secondary) }
        }
    }
    private func onboardingCard(_ progress: ProductOnboarding) -> some View {
        card {
            Text("开始前 · \(progress.step) / 6").font(.headline)
            switch progress.step {
            case 1:
                Text("慢慢认识自己的节律").font(.title2.bold())
                Text("FitCrew 帮你记录生活方式与感受，不作医疗诊断。你可以随时停止实验、撤回记录或删除账号。")
                Button("我已了解，继续") { advanceOnboarding(progress) }
            case 2:
                Text("选一个 90 天方向").font(.title2.bold())
                Button("前往旅程选择") { tab = 1 }
                Button("已保存方向，继续") { advanceOnboarding(progress) }.disabled(store.state?.journey == nil)
            case 3:
                Text("先了解数据用途").font(.title2.bold())
                Text("手动记录用于你的私人趋势和实验比较。Apple 健康按类别另行授权。AI 需要单独同意，不会自动读取笔记或原始健康样本；记录不会自动分享到群聊。")
                Button("已阅读用途，继续") { advanceOnboarding(progress) }
            case 4:
                Text("选择记录方式").font(.title2.bold())
                Button("查看 Apple 健康授权") {
                    Task { if await store.mutate("/v3/onboarding", body: ["step": progress.step, "route": "health"]) { showHealthConsent = true } }
                }
                Button("先用手动记录") { advanceOnboarding(progress, route: "manual") }
            case 5:
                Text("确认首次同步").font(.title2.bold())
                Text("授权不等于有样本。可以查看同步状态并重试，也可以先用手动记录。")
                Button("查看健康授权") { showHealthConsent = true }
                Text(model.statusMessage).font(.footnote)
                Text("最近同步：\(model.lastSyncText)").font(.footnote)
                if progress.route == "health" {
                    Button(model.isSyncing ? "正在同步…" : "开始或重试首次同步") {
                        Task { if await model.sync(fullReconciliation: true) { await store.refresh() } }
                    }
                    Button("检查同步并继续") { advanceOnboarding(progress) }
                }
                Button("暂用手动记录，继续") { advanceOnboarding(progress, route: "manual") }
            default:
                Text("做一次 Body Check").font(.title2.bold())
                Button("记录此刻感受") { tab = 3 }
                Button("已保存记录，完成引导") { advanceOnboarding(progress) }.disabled(store.state?.logs.isEmpty ?? true)
            }
            Text("确认后的进度保存在你的账号中，中断后可继续。").font(.footnote)
        }.disabled(store.busy || model.isSyncing)
    }
    private func advanceOnboarding(_ progress: ProductOnboarding, route: String? = nil) {
        var body: [String: Any] = ["step": progress.step]
        if let route { body["route"] = route }
        Task { await store.mutate("/v3/onboarding", body: body) }
    }
    private var journey: some View {
        Group {
            if let j = store.state?.journey { card { Text("90 DAY JOURNEY").font(.headline); Text(j.title).font(.largeTitle.bold()); Text("开始于 \(j.startDate.prefix(10)) · \(j.days) 天"); Text("持续记录感受、完成小行动，再用实验结果判断变化。") } }
            card {
                Text("接下来，想先改善什么？").font(.title2.bold())
                Picker("目标", selection: $goal) { Text("睡得更好").tag("sleep"); Text("更有精力").tag("energy"); Text("动得更多").tag("activity") }.pickerStyle(.segmented)
                Button(store.state?.journey == nil ? "开启 90 天旅程" : "更新目标") { Task { await store.mutate("/v3/journey", method: "PUT", body: ["goal": goal]) } }.buttonStyle(.borderedProminent).disabled(!model.isConfigured || store.busy)
            }
            if let trends = store.state?.trends { trendCard(trends) }
            card { Text("旅程足迹").font(.title2.bold()); Text("\(store.state?.logs.count ?? 0) 次身体记录"); ForEach(store.state?.experiments ?? []) { e in Text("\(e.title) · \(status(e.status))") }; Text("通过观察积累证据，暂不推断因果关系。").font(.footnote) }
        }
    }
    private func trendCard(_ trends: ProductTrends) -> some View {
        let points = Array(trends.points.suffix(trendDays))
        return card {
            Text("精力记录趋势").font(.title2.bold())
            Picker("观察窗口", selection: $trendDays) {
                Text("30 天").tag(30); Text("60 天").tag(60); Text("90 天").tag(90)
            }.pickerStyle(.segmented)
            Text("近 \(trendDays) 天 · \(points.filter { $0.count > 0 }.count) 天有记录 · \(points.filter { $0.count == 0 }.count) 天缺失")
            Text("范围 \(points.first?.date ?? trends.windowEnd) — \(trends.windowEnd) · 点击一天查看详情").font(.footnote)
            Text("来源：手动身体记录。同日取均值，精力 1–5 档；空缺表示未记录，不代表零分。不能据此判断行动效果。").font(.footnote)
            ScrollView(.horizontal) {
                LazyHStack(alignment: .bottom, spacing: 12) {
                    ForEach(points) { point in
                        VStack(spacing: 6) {
                            VStack { Spacer(minLength: 0)
                                if let energy = point.energy { RoundedRectangle(cornerRadius: 4).fill(green).frame(width: 20, height: CGFloat(energy * 20)) }
                                else { Text("—").foregroundStyle(.secondary) }
                            }.frame(height: 100)
                            Text(point.energy.map { $0.formatted() } ?? "缺失").font(.caption)
                            Text(point.date).font(.caption2)
                        }.frame(width: 82).contentShape(Rectangle()).onTapGesture { selectedTrend = point }.accessibilityElement(children: .combine).accessibilityAddTraits(.isButton).accessibilityAction { selectedTrend = point }
                    }
                }.padding(.vertical, 8)
            }
        }
    }
    private var experiments: some View {
        Group {
            card { Text("用一周，了解自己多一点").font(.title2.bold()); Text("默认使用规则建议；单独授权且服务可用时，可由 AI 选择实验。开始前可查看数据用途、方法和停止条件。"); Button("生成一个实验建议") { Task { await store.mutate("/v3/experiments/propose") } }.buttonStyle(.borderedProminent).disabled(!model.isConfigured || store.busy) }
            ForEach(store.state?.experiments ?? []) { e in card {
                Text(e.title).font(.title2.bold()); Text("\(status(e.status)) · \(e.durationDays) 天 · \(sourceLabel(e))").font(.subheadline); details(e)
                if let result = e.result { Text("实验结果").font(.headline); Text(result.display) }
                ForEach(e.actions, id: \.self) { action in Button(actionLabel(action)) { if action == "accept" { experiment = e } else if action == "stop" { stoppingExperiment = e } else { Task { await transition(e, action) } } }.frame(minHeight: 44).disabled(store.busy) }
            } }
        }
    }
    private func details(_ e: ProductExperiment) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(e.purpose ?? "用于本人的生活方式观察；开始前七天为基线，开始后七天为观察期。两窗各至少四个记录日才比较均值，不判断疗效。")
            if let start = e.baselineStart, let accepted = e.acceptedAt { Text("基线：\(start) — \(accepted)（不含开始时刻）").font(.footnote) }
            if let accepted = e.acceptedAt, let end = e.endsAt { Text("观察：\(accepted) — \(end)，暂停时段不计入。时间到且记录足够才能比较；不足会如实显示。").font(.footnote) }
            Text("假设：\(e.hypothesis)"); Text("行动：\(e.intervention)"); Text("持续时间：\(e.durationDays) 天"); Text("观察指标：\(e.metrics.joined(separator: "、"))"); Text("成功标准：\(e.successCriteria.joined(separator: "；"))"); Text("停止条件：\(e.stopConditions.joined(separator: "；"))"); Text("使用数据：\(e.dataCategories.joined(separator: "、"))"); Text("用于本人的实验评价，不会自动分享到群聊。").font(.footnote) }
    }
    private var logs: some View {
        Group {
            card {
                Text("Body Check").font(.title2.bold()); Stepper("精力 \(energy)/5", value: $energy, in: 1...5).frame(minHeight: 44); Stepper("压力 \(stress)/3", value: $stress, in: 1...3).frame(minHeight: 44)
                Picker("整体感受", selection: $feeling) { ForEach(["充沛", "正常", "有点累", "很累", "不适"], id: \.self) { Text($0) } }
                Picker("睡醒感受（可选）", selection: $sleepFeeling) { Text("暂不记录").tag(""); ForEach(["醒后清爽", "一般", "醒后疲惫"], id: \.self) { Text($0).tag($0) } }
                Picker("运动感受（可选）", selection: $trainingFeeling) { Text("暂不记录").tag(""); ForEach(["完成", "偏累", "恢复良好"], id: \.self) { Text($0).tag($0) } }
                Picker("压力来源（可选）", selection: $stressSource) { Text("暂不记录").tag(""); ForEach(["工作", "学习", "人际", "其他"], id: \.self) { Text($0).tag($0) } }
                if feeling == "不适" { Text("感到不适时，请先停止当前实验，必要时寻求专业帮助。"); Button("前往实验，选择停止") { tab = 2 } }
                TextField("还有什么想记下？（可选）", text: $note, axis: .vertical).lineLimit(3...6).padding(12).background(background, in: RoundedRectangle(cornerRadius: 12)); Text("\(note.count) / 500 字").font(.footnote)
                Button("保存身体记录") {
                    let submittedNote = note
                    let submittedSleep = sleepFeeling, submittedTraining = trainingFeeling, submittedSource = stressSource
                    var payload: [String: Any] = ["energy": energy, "stress": stress, "feeling": feeling, "note": submittedNote]
                    if !submittedSleep.isEmpty { payload["sleep_feeling"] = submittedSleep }
                    if !submittedTraining.isEmpty { payload["training_feeling"] = submittedTraining }
                    if !submittedSource.isEmpty { payload["stress_source"] = submittedSource }
                    Task {
                        if await store.mutate("/v3/logs", body: payload) {
                            if note == submittedNote { note = "" }
                            if sleepFeeling == submittedSleep { sleepFeeling = "" }
                            if trainingFeeling == submittedTraining { trainingFeeling = "" }
                            if stressSource == submittedSource { stressSource = "" }
                            saved = true
                        }
                    }
                }.buttonStyle(.borderedProminent).disabled(!model.isConfigured || store.busy || !BodyCheckInput.isValid(energy: energy, stress: stress, note: note))
                if saved { Text("记录已保存").foregroundStyle(green) }
            }.disabled(store.busy)
            if let receipt = store.receipt { Text("删除回执：\(receipt)").font(.footnote).textSelection(.enabled) }
            ForEach(Array((store.state?.logs ?? []).reversed())) { log in card { Text(log.feeling).font(.headline); Text("精力 \(log.energy)/5 · 压力 \(log.stress)/3"); if let value = log.sleepFeeling { Text("睡醒：\(value)") }; if let value = log.trainingFeeling { Text("运动：\(value)") }; if let value = log.stressSource { Text("压力来源：\(value)") }; if !log.note.isEmpty { Text(log.note) }; Text(log.createdAt).font(.footnote); Button("删除记录", role: .destructive) { deletion = "logs/\(log.id)" }.frame(minHeight: 44) } }
        }
    }
    private var profile: some View {
        Group {
            card {
                Text(model.isConfigured ? "已连接 FitCrew" : "连接你的 FitCrew").font(.title2.bold())
                if !model.isConfigured || store.requiresReauthentication { AppleAccountView(model: model).id(model.identityRevision) }
                if !model.isConfigured || store.requiresReauthentication { Text("已有邀请也可以用配对链接连接。"); SecureField("粘贴 fitcrew-health 配对链接", text: $pairing).textInputAutocapitalization(.never).autocorrectionDisabled(); Button("连接账号") { Task { if let url = URL(string: pairing.trimmingCharacters(in: .whitespacesAndNewlines)) { await model.configure(from: url); if model.isConfigured { pairing = ""; await store.refresh() } } } }.buttonStyle(.borderedProminent).disabled(pairing.isEmpty) }
                Text(model.statusMessage); Text("免费使用，无支付和提醒功能。").font(.footnote)
            }
            card {
                Text("可选的 AI 实验助手").font(.title2.bold())
                if let capability = store.capabilities {
                    Text(capability.ai_notice)
                    Text("服务提供方：\(capability.ai_provider)").font(.subheadline)
                    Text("只发送已授权的手动记录汇总天数与均值，不发送笔记或原始 Apple 健康样本。").font(.footnote)
                    if !capability.ai_available { Text("AI 服务尚未配置").foregroundStyle(.secondary) }
                    if capability.ai_consent_granted {
                        Text("已授权 · 可随时撤回")
                        Button("撤回 AI 数据授权", role: .destructive) { Task { await store.mutate("/v3/ai-consent", body: ["granted": false, "provider_notice_version": capability.ai_notice_version]) } }.frame(minHeight: 44).disabled(store.busy)
                    } else {
                        Button("我已阅读并同意授权 AI") { Task { await store.mutate("/v3/ai-consent", body: ["granted": true, "provider_notice_version": capability.ai_notice_version]) } }.frame(minHeight: 44).disabled(!capability.ai_available || store.busy)
                    }
                } else { Text("AI 服务尚未配置或未连接。连接账号后可查看提供方与数据说明。").foregroundStyle(.secondary) }
            }
            card {
                Label("Apple 健康", systemImage: "heart.fill").font(.title2.bold()); Text("读取你在系统选择授权的睡眠、活动、恢复与血糖数据。拒绝授权也可手动记录。"); Text("权限：\(model.authorizationStatus)"); Text("上次同步：\(model.lastSyncText)"); Text("系统不会告知每个读取类别是否被拒绝；没有样本不代表没有活动。").font(.footnote)
                Button("管理 Apple 健康授权") { showHealthConsent = true }.frame(minHeight: 44).disabled(!model.isConfigured)
                Button("立即同步") { Task { if await model.sync(fullReconciliation: false) { await store.refresh() } } }.frame(minHeight: 44).disabled(!model.isConfigured || store.busy)
            }
            card {
                Text("隐私与数据").font(.title2.bold()); Text("健康原始字段加密保存。私人数据不会自动进入群聊。可在健康 App 中撤回读取权限。")
                if let policyURL = ReleaseConfiguration.privacyPolicyURL {
                    Link("阅读完整隐私政策", destination: policyURL).frame(minHeight: 44)
                } else { Text("公开隐私政策尚未配置，正式登录暂不可用。").font(.footnote) }
                Button("导出我的数据") { Task { await store.exportData() } }.frame(minHeight: 44).disabled(!model.isConfigured || store.busy)
                if let url = store.exportURL { ShareLink("保存或分享导出文件", item: url).frame(minHeight: 44) }
                Button("删除全部数据", role: .destructive) { deletion = "data" }.frame(minHeight: 44).disabled(!model.isConfigured || store.busy)
                Button("注销账号", role: .destructive) { deletion = "account" }.frame(minHeight: 44).disabled(!model.isConfigured || store.busy)
                if let receipt = store.receipt { Text("删除已确认\n回执：\(receipt)").textSelection(.enabled) }
            }
        }
    }
    private func lighten(_ alternative: String) {
        guard let mission = lightenMission else { return }
        Task { if await store.mutate("/v3/mission", body: ["action": "lighten", "alternative": alternative, "mission_id": mission.id, "revision": mission.revision]) { showLighten = false } }
    }
    private func transition(_ e: ProductExperiment, _ action: String) async -> Bool { await store.mutate("/v3/experiments/\(e.id)/transition", body: ["action": action, "revision": e.revision]) }
    private func sourceLabel(_ e: ProductExperiment) -> String { e.source == "ai_selected" ? "AI 选择的实验" : "规则建议（非 AI）" }
    private func actionLabel(_ action: String) -> String { ["accept": "查看说明并开始", "pause": "暂停实验", "resume": "继续实验", "stop": "停止实验", "evaluate": "评估结果"][action] ?? action }
    private func status(_ value: String) -> String { ["proposed": "待确认", "pending": "待完成", "running": "进行中", "paused": "已暂停", "completed": "已完成", "stopped": "已停止", "done": "已完成", "skipped": "已跳过", "lightened": "已减轻"][value] ?? value }
}
