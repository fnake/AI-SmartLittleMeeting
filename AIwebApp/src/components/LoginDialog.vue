<script setup lang="ts">
import LoginForm from './LoginForm.vue'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

function onSuccess(): void {
  emit('success')
  emit('update:modelValue', false)
}
</script>

<template>
  <!-- token 失效 / 未登录时弹出的登录窗 -->
  <el-dialog
    :model-value="modelValue"
    title="登录小会"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <LoginForm @success="onSuccess" />
  </el-dialog>
</template>
