<script setup lang="ts">
const consentStore = useCookieConsentStore()
</script>

<template>
  <Transition name="cookie-banner">
    <div
      v-if="consentStore.status === 'pending'"
      class="fixed inset-0 z-[70] flex items-end justify-center p-4"
    >
      <!-- 背景オーバーレイ -->
      <div class="absolute inset-0 bg-black/40" />

      <!-- バナー本体 -->
      <div
        class="relative w-full max-w-2xl bg-surface-800 border border-surface-600 rounded-lg shadow-2xl p-6"
      >
        <div class="flex items-start gap-3 mb-4">
          <i class="pi pi-chart-bar text-primary-400 text-xl mt-0.5 shrink-0" />
          <div>
            <h3 class="font-semibold text-surface-100 mb-1">アクセス解析について</h3>
            <p class="text-sm text-surface-300 leading-relaxed">
              このツールでは、利用状況の把握を目的として Google Analytics 4
              を使用しています。同意いただいた場合のみ、匿名のアクセスデータが Google
              に送信されます。「使用しない」を選択した場合、データは一切収集されません。
            </p>
          </div>
        </div>

        <div class="flex gap-3 justify-end">
          <Button
            label="使用しない"
            severity="secondary"
            size="small"
            @click="consentStore.decline()"
          />
          <Button label="同意する" size="small" @click="consentStore.accept()" />
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cookie-banner-enter-active,
.cookie-banner-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.cookie-banner-enter-from,
.cookie-banner-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
