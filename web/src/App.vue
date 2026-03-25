<script setup lang="ts">
const base = import.meta.env.BASE_URL

const { mode: colorMode } = useAppColorMode()

const colorModeOptions: {
  value: import('@/composables/app-color-mode').ColorMode
  icon: string
  label: string
}[] = [
  { value: 'light', icon: 'pi pi-sun', label: 'ライト' },
  { value: 'dark', icon: 'pi pi-moon', label: 'ダーク' },
  { value: 'system', icon: 'pi pi-desktop', label: 'システム' },
]

const { releases, loading: releasesLoading, error: releasesError } = useReleases()

const latestRelease = computed(() => releases.value[0] ?? null)
const pastReleases = computed(() => releases.value.slice(1))

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatBytes(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const requirements = [
  { label: 'OS', value: 'Windows 11 / Windows 10' },
  { label: '権限', value: '管理者権限で実行' },
  { label: 'ウィンドウサイズ', value: '1280×720（最大のみ対応）' },
]

const steps = [
  { text: 'ゲームを起動し、究極錬成の装備一覧画面を開く', note: null },
  { text: 'ツールを起動する', note: 'ゲームが起動していない場合はエラーになります' },
  { text: 'キャプチャ表示に装備一覧画面が映り、装備情報が自動検出されるのを待つ', note: null },
  { text: '完了条件・中断条件を設定する', note: null },
  { text: '「開始」ボタンを押す', note: null },
  { text: '自動処理が始まります。停止するには Esc キーまたは停止ボタン', note: null },
]

interface UiChild {
  name: string
  desc: string
}
interface UiItem {
  no: string
  name: string
  desc: string
  children?: UiChild[]
}

const uiItems: UiItem[] = [
  {
    no: '①',
    name: 'キャプチャ表示',
    desc: 'ゲーム画面のリアルタイムプレビュー。ゲームウィンドウが検出されていることを確認してから開始してください',
  },
  {
    no: '②',
    name: '選択中の装備情報',
    desc: '自動検出された装備名・種類と、サブステータス4枠の現在の効果名・値・ロック状態',
  },
  {
    no: '③',
    name: '消費アイテム',
    desc: '画面から読み取った錬成Ptとマナの現在残量',
  },
  {
    no: '④',
    name: '開始 / 停止ボタン',
    desc: '自動化の開始・停止。停止はゲーム画面にフォーカスがある状態でも Esc キーで可能',
  },
  {
    no: '⑤',
    name: '完了条件設定',
    desc: '条件を満たした結果が出た時点で自動停止します',
    children: [
      { name: '目標ステータス', desc: '揃えたい効果の種類（例：HP強化）' },
      { name: '最低値', desc: 'その効果の最低限欲しい数値' },
      { name: '必要枠数', desc: '何枠以上揃えば完了とするか（ロック中のものを含みます）' },
    ],
  },
  {
    no: '⑥',
    name: '中断条件設定',
    desc: '錬成Ptが指定値を下回ったら自動停止します',
  },
  {
    no: '⑦',
    name: 'その他設定',
    desc: 'キャプチャ間隔（負荷状況に応じて調整ください）・ゲームウィンドウへのツール自動追従の設定',
  },
  {
    no: '⑧',
    name: 'ステータスバー',
    desc: '現在の動作状態・今回の錬成回数・起動後の累計錬成回数',
  },
]
</script>

<template>
  <CookieConsentBanner />

  <div class="min-h-screen bg-surface-100 text-surface-900 dark:bg-surface-900 dark:text-surface-0">
    <!-- ヘッダー -->
    <header
      class="sticky top-0 z-10 border-b border-surface-200 bg-surface-0/90 backdrop-blur dark:border-surface-700 dark:bg-surface-800/90"
    >
      <div class="mx-auto flex h-14 max-w-[960px] items-center justify-between px-4">
        <span class="font-bold">プリコネR 究極錬成自動化ツール</span>
        <div class="flex items-center gap-3">
          <!-- カラーモード切替 -->
          <div
            class="flex overflow-hidden rounded-md border border-surface-200 dark:border-surface-700"
          >
            <button
              v-for="opt in colorModeOptions"
              :key="opt.value"
              :title="opt.label"
              class="px-2.5 py-1.5 transition-colors"
              :class="
                colorMode === opt.value
                  ? 'bg-surface-200 text-surface-900 dark:bg-surface-600 dark:text-surface-0'
                  : 'text-surface-400 hover:text-surface-700 dark:hover:text-surface-300'
              "
              @click="colorMode = opt.value"
            >
              <i :class="opt.icon" class="text-sm" />
            </button>
          </div>
          <a
            href="https://github.com/imo-tikuwa/pricone-re-synthesis"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-1.5 text-surface-500 transition-colors hover:text-surface-700 dark:hover:text-surface-200"
          >
            <i class="pi pi-github text-xl" />
            <span class="text-sm">GitHub</span>
          </a>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-[960px] space-y-16 px-4 py-12">
      <!-- ヒーロー -->
      <section
        class="overflow-hidden rounded-xl border border-surface-200 bg-surface-0 shadow-sm dark:border-surface-700 dark:bg-surface-800"
      >
        <div class="flex flex-col lg:flex-row">
          <!-- 左: テキスト・ダウンロード -->
          <div class="flex-1 min-w-0 flex flex-col justify-center space-y-6 px-8 py-10">
            <h1 class="text-3xl font-bold leading-snug">プリコネR<br />究極錬成自動化ツール</h1>
            <p class="text-surface-600 dark:text-surface-300">
              究極錬成の繰り返し作業を自動化するツールです。<br />
              目標の効果・数値が揃うまで錬成・判定・ロックを自動で行います。
            </p>
            <div>
              <template v-if="releasesLoading">
                <Skeleton width="180px" height="38px" border-radius="6px" />
              </template>
              <template v-else-if="latestRelease?.assets[0]">
                <Button
                  as="a"
                  :href="latestRelease.assets[0].browser_download_url"
                  icon="pi pi-download"
                  :label="`ダウンロード ${latestRelease.tag_name}`"
                />
              </template>
              <template v-else-if="releasesError">
                <span class="text-sm text-surface-500">リリース情報の取得に失敗しました</span>
              </template>
            </div>
          </div>
          <!-- 右: デモ動画 -->
          <div
            class="flex justify-end border-t border-surface-200 dark:border-surface-700 lg:border-t-0 lg:border-l"
          >
            <video
              :src="`${base}images/tool-movie.mp4`"
              controls
              muted
              class="h-[420px] w-auto object-cover"
            />
          </div>
        </div>
      </section>

      <Divider />

      <!-- 動作要件 -->
      <section class="space-y-4">
        <h2 class="border-l-4 border-surface-400 pl-3 text-2xl font-bold dark:border-surface-500">
          動作要件
        </h2>
        <table class="w-full border-collapse text-sm">
          <tbody>
            <tr
              v-for="req in requirements"
              :key="req.label"
              class="border-b border-surface-200 last:border-0 dark:border-surface-700"
            >
              <td class="w-40 py-3 pr-8 text-surface-500">{{ req.label }}</td>
              <td class="py-3 font-medium">{{ req.value }}</td>
            </tr>
          </tbody>
        </table>
        <Message severity="warn" :closable="false">
          UAC の「不明な発行元」警告は署名なしのため正常です。「はい」を選択して続行してください。
        </Message>
      </section>

      <Divider />

      <!-- 注意事項 -->
      <section class="space-y-4">
        <h2 class="border-l-4 border-surface-400 pl-3 text-2xl font-bold dark:border-surface-500">
          注意事項
        </h2>
        <Message severity="warn" :closable="false">
          <ul class="space-y-2">
            <li>ゲーム画面の上に別のウィンドウを重ねないでください（画面認識が失敗します）</li>
            <li>
              自動処理中はマウス・キーボードを操作しないでください（マウスカーソルを制御しているため操作が競合します）
            </li>
            <li>停止したいときは Esc キーを押してください</li>
          </ul>
        </Message>
      </section>

      <Divider />

      <!-- 使い方 -->
      <section class="space-y-6">
        <h2 class="border-l-4 border-surface-400 pl-3 text-2xl font-bold dark:border-surface-500">
          使い方
        </h2>
        <ol class="space-y-4">
          <li v-for="(step, i) in steps" :key="i" class="flex items-start gap-4">
            <span
              class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2 border-surface-300 text-sm font-bold text-surface-600 dark:border-surface-600 dark:text-surface-300"
            >
              {{ i + 1 }}
            </span>
            <div class="pt-1">
              <span>{{ step.text }}</span>
              <span v-if="step.note" class="mt-0.5 block text-sm text-surface-500"
                >※ {{ step.note }}</span
              >
            </div>
          </li>
        </ol>
      </section>

      <Divider />

      <!-- 画面説明 -->
      <section class="space-y-6">
        <h2 class="border-l-4 border-surface-400 pl-3 text-2xl font-bold dark:border-surface-500">
          画面説明
        </h2>
        <div class="flex flex-col items-start gap-8 lg:flex-row">
          <!-- スクリーンショット -->
          <div class="flex-shrink-0">
            <img
              :src="`${base}images/tool-screenshot-annotated.png`"
              alt="ツールのスクリーンショット"
              class="w-full rounded-lg border border-surface-200 dark:border-surface-700 lg:max-w-[460px]"
              style="clip-path: inset(2px)"
            />
          </div>
          <!-- テーブル -->
          <div class="min-w-0 flex-1">
            <table class="w-full border-collapse text-sm">
              <thead>
                <tr class="border-b-2 border-surface-200 dark:border-surface-700">
                  <th class="w-8 py-2 pr-4 text-left font-medium text-surface-500">No.</th>
                  <th class="py-2 pr-4 text-left font-medium text-surface-500">項目名</th>
                  <th class="py-2 text-left font-medium text-surface-500">説明</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="item in uiItems" :key="item.no">
                  <tr class="border-b border-surface-200 dark:border-surface-700">
                    <td class="py-2.5 pr-4 text-base font-bold text-surface-500">{{ item.no }}</td>
                    <td class="whitespace-nowrap py-2.5 pr-4 font-medium">{{ item.name }}</td>
                    <td class="py-2.5 text-surface-600 dark:text-surface-400">{{ item.desc }}</td>
                  </tr>
                  <tr
                    v-for="child in item.children"
                    :key="child.name"
                    class="border-b border-surface-200 dark:border-surface-700"
                  >
                    <td class="py-1.5 pr-4" />
                    <td class="whitespace-nowrap py-1.5 pl-4 pr-4 text-surface-500">
                      └ {{ child.name }}
                    </td>
                    <td class="py-1.5 text-xs text-surface-500">{{ child.desc }}</td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <Divider />

      <!-- リリース一覧 -->
      <section class="space-y-6">
        <h2 class="border-l-4 border-surface-400 pl-3 text-2xl font-bold dark:border-surface-500">
          リリース
        </h2>

        <template v-if="releasesLoading">
          <Skeleton height="140px" border-radius="8px" />
        </template>

        <template v-else-if="releasesError">
          <Message severity="error" :closable="false">リリース情報の取得に失敗しました。</Message>
        </template>

        <template v-else>
          <!-- 最新リリース -->
          <div
            v-if="latestRelease"
            class="space-y-4 rounded-lg border border-surface-200 bg-surface-0 p-6 shadow-sm dark:border-surface-700 dark:bg-surface-800"
          >
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-xl font-bold">{{ latestRelease.tag_name }}</span>
              <Tag value="最新" severity="success" />
              <span class="text-sm text-surface-500">{{
                formatDate(latestRelease.published_at)
              }}</span>
            </div>
            <div
              v-if="latestRelease.assets[0]"
              class="space-y-1 text-sm text-surface-600 dark:text-surface-400"
            >
              <div>ファイル: {{ latestRelease.assets[0].name }}</div>
              <div>サイズ: {{ formatBytes(latestRelease.assets[0].size) }}</div>
              <div>
                ダウンロード数:
                {{ latestRelease.assets[0].download_count.toLocaleString('ja-JP') }}
              </div>
            </div>
            <div class="flex flex-wrap gap-3">
              <Button
                v-if="latestRelease.assets[0]"
                as="a"
                :href="latestRelease.assets[0].browser_download_url"
                icon="pi pi-download"
                :label="`${latestRelease.tag_name} をダウンロード`"
              />
              <Button
                as="a"
                :href="latestRelease.html_url"
                target="_blank"
                rel="noopener noreferrer"
                icon="pi pi-external-link"
                label="リリースノート"
                severity="secondary"
                outlined
              />
            </div>
          </div>

          <!-- 過去のリリース -->
          <div v-if="pastReleases.length > 0" class="space-y-2">
            <h3 class="font-semibold text-surface-600 dark:text-surface-400">過去のバージョン</h3>
            <div
              v-for="release in pastReleases"
              :key="release.tag_name"
              class="flex flex-wrap items-center gap-4 rounded-lg border border-surface-200 px-4 py-3 dark:border-surface-700"
            >
              <span class="font-medium">{{ release.tag_name }}</span>
              <span class="text-sm text-surface-500">{{ formatDate(release.published_at) }}</span>
              <span v-if="release.assets[0]" class="text-sm text-surface-400">
                {{ release.assets[0].download_count.toLocaleString('ja-JP') }} DL
              </span>
              <div class="ml-auto flex gap-2">
                <Button
                  v-if="release.assets[0]"
                  as="a"
                  :href="release.assets[0].browser_download_url"
                  icon="pi pi-download"
                  size="small"
                  severity="secondary"
                  outlined
                />
                <Button
                  as="a"
                  :href="release.html_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  icon="pi pi-external-link"
                  size="small"
                  severity="secondary"
                  outlined
                />
              </div>
            </div>
          </div>
        </template>
      </section>
    </main>

    <!-- 免責事項 -->
    <section class="mx-auto max-w-[960px] px-4 pb-16">
      <Divider />
      <div
        class="space-y-1 rounded-lg border border-surface-200 bg-surface-0 px-6 py-5 text-sm text-surface-500 dark:border-surface-700 dark:bg-surface-800"
      >
        <p class="font-semibold text-surface-600 dark:text-surface-400">免責事項</p>
        <p>本ツールは非公式のファンメイドツールであり、Cygames とは一切関係ありません。</p>
        <p>
          本ツールの使用によって生じたいかなる損害・不利益（アカウント停止・データ消失・動作不良等）についても、作者は一切の責任を負いません。
        </p>
        <p>利用は自己責任で行ってください。</p>
      </div>
    </section>

    <!-- フッター -->
    <footer class="border-t border-surface-200 py-6 dark:border-surface-700">
      <div class="mx-auto max-w-[960px] px-4 text-center text-sm text-surface-400">
        <a
          href="https://github.com/imo-tikuwa/pricone-re-synthesis"
          target="_blank"
          rel="noopener noreferrer"
          class="transition-colors hover:text-surface-600 dark:hover:text-surface-300"
        >
          imo-tikuwa/pricone-re-synthesis
        </a>
      </div>
    </footer>
  </div>
</template>
