<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { ApiRequestError, getToken } from '@/api'
import { useAuth } from '@/composables/useAuth'

const emit = defineEmits<{ (e: 'success'): void }>()

const { loginAsGuest, loginByPassword, registerAccount } = useAuth()

const mode = ref<'login' | 'register'>('login')
const formRef = ref<FormInstance>()
const submitting = ref(false)
// 注册时是否携带当前游客 token（游客转正，历史数据保留）
const keepGuestData = ref(getToken() !== null)

const form = reactive({
  phone: '',
  password: '',
  confirm: '',
})

const rules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '请输入正确的 11 位手机号', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [{ required: true, message: '请再次输入密码', trigger: 'blur' }],
}

function fail(error: unknown): void {
  if (error instanceof ApiRequestError) {
    ElMessage.error(error.message)
  } else {
    ElMessage.error('操作失败，请重试')
  }
}

async function submit(): Promise<void> {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (valid !== true) return
  if (mode.value === 'register' && form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await loginByPassword(form.phone, form.password)
      ElMessage.success('登录成功')
    } else {
      const res = await registerAccount(form.phone, form.password, keepGuestData.value)
      if (keepGuestData.value) {
        ElMessage.success(res.message ?? '注册成功，历史数据已保留')
      } else {
        // 普通注册：需要再登录
        ElMessage.success(res.message ?? '注册成功，请登录')
        mode.value = 'login'
        return
      }
    }
    emit('success')
  } catch (error) {
    fail(error)
  } finally {
    submitting.value = false
  }
}

async function guestLogin(): Promise<void> {
  if (submitting.value) return
  submitting.value = true
  try {
    await loginAsGuest()
    ElMessage.success('已进入游客模式')
    emit('success')
  } catch (error) {
    fail(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
    <el-tabs v-model="mode" stretch>
      <el-tab-pane label="登录" name="login" />
      <el-tab-pane label="注册" name="register" />
    </el-tabs>

    <el-form-item label="手机号" prop="phone">
      <el-input v-model="form.phone" placeholder="11 位手机号" maxlength="11" clearable />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input
        v-model="form.password"
        type="password"
        placeholder="至少 6 位"
        show-password
        @keyup.enter="submit"
      />
    </el-form-item>
    <el-form-item v-if="mode === 'register'" label="确认密码" prop="confirm">
      <el-input
        v-model="form.confirm"
        type="password"
        placeholder="再次输入密码"
        show-password
        @keyup.enter="submit"
      />
    </el-form-item>

    <el-form-item v-if="mode === 'register' && getToken() !== null">
      <el-checkbox v-model="keepGuestData">
        保留当前游客数据（游客转正，话题与记忆无缝迁移）
      </el-checkbox>
    </el-form-item>

    <el-button
      type="primary"
      class="submit-btn"
      :loading="submitting"
      @click="submit"
    >
      {{ mode === 'login' ? '登录' : '注册' }}
    </el-button>

    <el-divider>
      <span class="divider-text">或</span>
    </el-divider>

    <el-button class="guest-btn" :disabled="submitting" @click="guestLogin">
      游客模式直接体验
    </el-button>
  </el-form>
</template>

<style scoped>
.submit-btn,
.guest-btn {
  width: 100%;
}

.divider-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
