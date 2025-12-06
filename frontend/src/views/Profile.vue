<template>
  <div class="profile-page">
    <div class="container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>正在加载用户信息...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        <h2>加载失败</h2>
        <p>{{ error }}</p>
        <button @click="loadUserData" class="retry-button">重试</button>
      </div>

      <!-- 用户信息内容 -->
      <div v-else-if="userProfile" class="profile-content">
        <!-- 用户头部信息 -->
        <div class="profile-header">
          <div class="user-avatar">
            <div class="avatar-circle">
              {{ userProfile.username.charAt(0).toUpperCase() }}
            </div>
            <div class="user-info">
              <h1>{{ userProfile.username }}</h1>
              <p class="user-email">{{ userProfile.email }}</p>
              <div class="user-meta">
                <span class="role-badge" :class="userProfile.role">
                  {{ getRoleText(userProfile.role) }}
                </span>
                <span class="join-date">
                  {{ formatDate(userProfile.created_at) }} 加入
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 统计摘要 -->
        <StatsSummary
          :profile="userProfile"
          :history-stats="historyResponse?.stats"
          :showDetailed="true"
        />

        <!-- 标签页导航 -->
        <div class="tabs-container">
          <div class="tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="activeTab = tab.key"
              :class="['tab-button', { active: activeTab === tab.key }]"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <!-- 标签页内容 -->
        <div class="tab-content">
          <!-- 历史记录标签页 -->
          <div v-if="activeTab === 'history'" class="history-content">
            <HistoryTable
              :records="historyResponse?.records || []"
              :loading="historyLoading"
              :hasMore="hasMoreHistory"
              @load-more="loadMoreHistory"
            />
          </div>

          <!-- 设置标签页 -->
          <div v-if="activeTab === 'settings'" class="settings-content">
            <div class="settings-grid">
              <!-- 基本信息 -->
              <div class="settings-section">
                <h3>基本信息</h3>
                <div class="form-grid">
                  <div class="form-group">
                    <label>用户名</label>
                    <input
                      v-model="editProfile.username"
                      type="text"
                      class="form-input"
                      :disabled="updatingProfile"
                    />
                  </div>
                  <div class="form-group">
                    <label>邮箱</label>
                    <input
                      v-model="editProfile.email"
                      type="email"
                      class="form-input"
                      :disabled="updatingProfile"
                    />
                  </div>
                  <div class="form-group">
                    <label>手机号</label>
                    <input
                      v-model="editProfile.phone"
                      type="tel"
                      class="form-input"
                      :disabled="updatingProfile"
                      placeholder="请输入手机号"
                    />
                  </div>
                  <div class="form-group">
                    <label>时区</label>
                    <select
                      v-model="editProfile.timezone"
                      class="form-input"
                      :disabled="updatingProfile"
                    >
                      <option value="Asia/Shanghai">Asia/Shanghai</option>
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">America/New_York</option>
                      <option value="Europe/London">Europe/London</option>
                    </select>
                  </div>
                </div>
                <div class="form-actions">
                  <button
                    @click="saveProfile"
                    :disabled="updatingProfile"
                    class="save-button"
                  >
                    {{ updatingProfile ? '保存中...' : '保存更改' }}
                  </button>
                </div>
              </div>

              <!-- 通知设置 -->
              <div class="settings-section">
                <h3>通知设置</h3>
                <div class="notification-settings">
                  <div class="setting-item">
                    <label class="toggle-label">
                      <input
                        v-model="editProfile.notification_settings.email_notifications"
                        type="checkbox"
                        class="toggle-input"
                        :disabled="updatingProfile"
                      />
                      <span class="toggle-text">邮件通知</span>
                    </label>
                    <p class="setting-description">接收重要的账户和安全相关邮件</p>
                  </div>
                  <div class="setting-item">
                    <label class="toggle-label">
                      <input
                        v-model="editProfile.notification_settings.prediction_reminders"
                        type="checkbox"
                        class="toggle-input"
                        :disabled="updatingProfile"
                      />
                      <span class="toggle-text">预测提醒</span>
                    </label>
                    <p class="setting-description">比赛开始前收到预测提醒</p>
                  </div>
                  <div class="setting-item">
                    <label class="toggle-label">
                      <input
                        v-model="editProfile.notification_settings.result_notifications"
                        type="checkbox"
                        class="toggle-input"
                        :disabled="updatingProfile"
                      />
                      <span class="toggle-text">结果通知</span>
                    </label>
                    <p class="setting-description">比赛结束后收到结果通知</p>
                  </div>
                </div>
              </div>

              <!-- 账户安全 -->
              <div class="settings-section">
                <h3>账户安全</h3>
                <div class="security-actions">
                  <div class="action-item">
                    <div class="action-content">
                      <h4>修改密码</h4>
                      <p>定期更改密码以提高账户安全性</p>
                    </div>
                    <button class="action-button">修改</button>
                  </div>
                  <div class="action-item">
                    <div class="action-content">
                      <h4>两步验证</h4>
                      <p>启用两步验证增强账户安全</p>
                    </div>
                    <button class="action-button secondary">设置</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import { UserProfile, UserUpdateData, HistoryResponse } from '@/types/prediction'
import StatsSummary from '@/components/profile/StatsSummary.vue'
import HistoryTable from '@/components/profile/HistoryTable.vue'

const authStore = useAuthStore()

// 响应式数据
const loading = ref(true)
const error = ref<string>('')
const userProfile = ref<UserProfile | null>(null)
const historyResponse = ref<HistoryResponse | null>(null)
const historyLoading = ref(false)
const updatingProfile = ref(false)
const activeTab = ref('history')
const historyPage = ref(1)
const historyPageSize = 20

// 编辑表单数据
const editProfile = ref<UserUpdateData>({
  username: '',
  email: '',
  phone: '',
  timezone: 'Asia/Shanghai',
  notification_settings: {
    email_notifications: true,
    prediction_reminders: true,
    result_notifications: true
  }
})

// 标签页配置
const tabs = [
  { key: 'history', label: '历史记录' },
  { key: 'settings', label: '账户设置' }
]

// 计算属性
const hasMoreHistory = computed(() => {
  if (!historyResponse.value) return false
  return historyResponse.value.records.length < historyResponse.value.total
})

// 加载用户数据
const loadUserData = async () => {
  try {
    loading.value = true
    error.value = ''

    // 并行加载用户信息
    const [profileData, historyData] = await Promise.all([
      apiClient.getUserProfile(),
      loadHistoryData()
    ])

    userProfile.value = profileData

    // 初始化编辑表单
    editProfile.value = {
      username: profileData.username,
      email: profileData.email,
      phone: profileData.phone || '',
      timezone: profileData.timezone || 'Asia/Shanghai',
      notification_settings: {
        email_notifications: true,
        prediction_reminders: true,
        result_notifications: true
      }
    }

    // 更新 auth store 中的用户数据
    authStore.setUser(profileData)

  } catch (err) {
    console.error('Failed to load user data:', err)
    error.value = err instanceof Error ? err.message : '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

// 加载历史数据
const loadHistoryData = async (page: number = 1): Promise<HistoryResponse> => {
  try {
    historyLoading.value = true
    const response = await apiClient.getUserHistory(page, historyPageSize)

    if (page === 1) {
      historyResponse.value = response
    } else {
      // 追加加载更多记录
      if (historyResponse.value) {
        historyResponse.value.records = [...historyResponse.value.records, ...response.records]
      }
    }

    return response
  } catch (err) {
    console.error('Failed to load history:', err)
    throw err
  } finally {
    historyLoading.value = false
  }
}

// 加载更多历史记录
const loadMoreHistory = async () => {
  if (!hasMoreHistory.value || historyLoading.value) return

  historyPage.value++
  await loadHistoryData(historyPage.value)
}

// 保存用户资料
const saveProfile = async () => {
  try {
    updatingProfile.value = true

    if (!userProfile.value) return

    const updatedProfile = await apiClient.updateUserProfile(editProfile.value)

    // 更新本地状态
    userProfile.value = updatedProfile

    // 更新 auth store
    authStore.setUser(updatedProfile)

    alert('个人资料已更新成功！')

  } catch (err) {
    console.error('Failed to update profile:', err)
    alert('更新失败，请重试')
  } finally {
    updatingProfile.value = false
  }
}

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// 获取角色文本
const getRoleText = (role: string): string => {
  const roleMap: Record<string, string> = {
    'admin': '管理员',
    'user': '普通用户'
  }
  return roleMap[role] || role
}

// 页面加载时获取数据
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f9fafb;
  padding: 1rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* 加载和错误状态 */
.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state h2 {
  color: #dc2626;
  margin-bottom: 0.5rem;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.retry-button:hover {
  background: #2563eb;
}

/* 用户头部 */
.profile-header {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.user-avatar {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.avatar-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.user-info h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.875rem;
  font-weight: 700;
  color: #1f2937;
}

.user-email {
  margin: 0 0 0.5rem 0;
  color: #6b7280;
  font-size: 1rem;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.role-badge.admin {
  background: #fef3c7;
  color: #d97706;
}

.role-badge.user {
  background: #dbeafe;
  color: #1e40af;
}

.join-date {
  color: #6b7280;
  font-size: 0.875rem;
}

/* 标签页 */
.tabs-container {
  background: white;
  border-radius: 8px;
  padding: 0;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
}

.tab-button {
  flex: 1;
  padding: 1rem;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
  color: #6b7280;
  transition: all 0.2s;
}

.tab-button:hover {
  background: #f9fafb;
}

.tab-button.active {
  color: #3b82f6;
  border-bottom: 2px solid #3b82f6;
}

/* 标签页内容 */
.tab-content {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 设置页面 */
.settings-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

.settings-section {
  background: #f9fafb;
  padding: 1.5rem;
  border-radius: 8px;
}

.settings-section h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.form-input {
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input:disabled {
  background: #f3f4f6;
  color: #6b7280;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.save-button {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.save-button:hover:not(:disabled) {
  background: #2563eb;
}

.save-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 通知设置 */
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.setting-item {
  padding: 1rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
}

.toggle-input {
  width: 1.25rem;
  height: 1.25rem;
  accent-color: #3b82f6;
}

.toggle-text {
  font-weight: 600;
  color: #1f2937;
}

.setting-description {
  margin: 0.5rem 0 0 2rem;
  font-size: 0.875rem;
  color: #6b7280;
}

/* 安全设置 */
.security-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.action-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.action-content h4 {
  margin: 0 0 0.25rem 0;
  font-weight: 600;
  color: #1f2937;
}

.action-content p {
  margin: 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.action-button {
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.action-button:hover {
  background: #2563eb;
}

.action-button.secondary {
  background: #6b7280;
}

.action-button.secondary:hover {
  background: #4b5563;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-header {
    padding: 1.5rem;
  }

  .user-avatar {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .user-info h1 {
    font-size: 1.5rem;
  }

  .user-meta {
    flex-direction: column;
    gap: 0.5rem;
  }

  .tabs {
    flex-direction: column;
  }

  .settings-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .action-item {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 0.5rem;
  }

  .profile-header {
    padding: 1rem;
  }

  .avatar-circle {
    width: 60px;
    height: 60px;
    font-size: 1.5rem;
  }

  .settings-section {
    padding: 1rem;
  }
}
</style>