<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/funds'
import { aiAPI, settingsAPI } from '@/api'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const fundStore = useFundStore()

// 设置数据
const generalSettings = ref({
  total_position_amount: ''
})

const aiSettings = ref({
  api_key: '',
  base_url: '',
  model: 'deepseek-chat',
  api_key_configured: false
})

const dbConfig = ref({
  type: 'sqlite',
  sqlite_path: './data/funds.db',
  pg_host: 'localhost',
  pg_port: '5432',
  pg_name: 'funds',
  pg_user: '',
  pg_password: ''
})

const dbStatus = ref(null)
const dbConnectionStatus = ref(null)
const testingConnection = ref(false)
const initializingDb = ref(false)

// 提示词设置
const promptType = ref('fund')
const promptConfig = ref({
  fund_analysis: { system_prompt: '', user_prompt: '' },
  portfolio_analysis: { system_prompt: '', user_prompt: '' }
})

// 基金分析变量
const fundVariables = [
  { name: 'fund_name', desc: '基金名称' },
  { name: 'fund_code', desc: '基金代码' },
  { name: 'fund_type', desc: '基金类型' },
  { name: 'risk_level', desc: '风险等级' },
  { name: 'current_value', desc: '当前净值' },
  { name: 'change_5d', desc: '近5日涨跌幅' },
  { name: 'change_20d', desc: '近20日涨跌幅' },
  { name: 'ma5', desc: 'MA5均线' },
  { name: 'ma10', desc: 'MA10均线' },
  { name: 'ma20', desc: 'MA20均线' },
  { name: 'rsi', desc: 'RSI指标' },
  { name: 'macd', desc: 'MACD指标' },
  { name: 'etf_info', desc: '关联ETF信息' },
  { name: 'holding_info', desc: '持仓信息' },
  { name: 'position_info', desc: '仓位信息' },
  { name: 'market_sentiment', desc: '市场情绪' },
  { name: 'fund_detail', desc: '基金详情' },
  { name: 'risk_metrics', desc: '风险指标' },
  { name: 'related_news', desc: '相关新闻' }
]

const portfolioVariables = [
  { name: 'account_summary', desc: '账户汇总' },
  { name: 'holdings_detail', desc: '持仓明细' }
]

// 加载设置
async function loadSettings() {
  try {
    const [settings, dbResult, promptsResult, dbConnResult] = await Promise.all([
      aiAPI.getSettings(),
      settingsAPI.getDatabaseConfig(),
      settingsAPI.getPrompts(),
      settingsAPI.getDatabaseStatus().catch(() => null)
    ])
    
    // 加载通用设置
    generalSettings.value.total_position_amount = settings.total_position_amount || ''
    
    // 加载 AI 设置
    aiSettings.value = {
      api_key: '',
      base_url: settings.deepseek_base_url || 'https://api.deepseek.com/v1',
      model: settings.deepseek_model || 'deepseek-chat',
      api_key_configured: settings.api_key_configured || false
    }
    
    // 加载数据库配置到表单
    if (dbResult) {
      dbConfig.value.type = dbResult.type || 'sqlite'
      dbConfig.value.sqlite_path = dbResult.sqlite?.path || './data/funds.db'
      dbConfig.value.pg_host = dbResult.postgresql?.host || 'localhost'
      dbConfig.value.pg_port = dbResult.postgresql?.port || '5432'
      dbConfig.value.pg_name = dbResult.postgresql?.name || 'funds'
      dbConfig.value.pg_user = dbResult.postgresql?.user || ''
      dbConfig.value.pg_password = ''
      dbStatus.value = dbResult
    }
    
    // 加载数据库连接状态
    dbConnectionStatus.value = dbConnResult
    
    // 正确处理提示词数据结构
    if (promptsResult && promptsResult.prompts) {
      promptConfig.value = promptsResult.prompts
    }
  } catch (error) {
    console.error('加载设置失败:', error)
  }
}

// 保存设置
async function saveAllSettings() {
  try {
    // 保存通用设置
    await aiAPI.updatePositionSetting({ total_position_amount: generalSettings.value.total_position_amount })
    
    // 保存 AI 设置
    const aiData = {}
    if (aiSettings.value.api_key) aiData.deepseek_api_key = aiSettings.value.api_key
    if (aiSettings.value.base_url) aiData.deepseek_base_url = aiSettings.value.base_url
    if (aiSettings.value.model) aiData.deepseek_model = aiSettings.value.model
    if (Object.keys(aiData).length > 0) {
      await aiAPI.updateSettings(aiData)
    }
    
    // 保存提示词 - 转换为后端期望的格式
    const promptsData = {
      fund_analysis_system: promptConfig.value.fund_analysis?.system_prompt || null,
      fund_analysis_user: promptConfig.value.fund_analysis?.user_prompt || null,
      portfolio_analysis_system: promptConfig.value.portfolio_analysis?.system_prompt || null,
      portfolio_analysis_user: promptConfig.value.portfolio_analysis?.user_prompt || null
    }
    await settingsAPI.updatePrompts(promptsData)
    
    // 保存数据库配置
    const dbData = {
      db_type: dbConfig.value.type,
      sqlite_path: dbConfig.value.sqlite_path,
      pg_host: dbConfig.value.pg_host,
      pg_port: dbConfig.value.pg_port,
      pg_name: dbConfig.value.pg_name,
      pg_user: dbConfig.value.pg_user,
      pg_password: dbConfig.value.pg_password  // 如果为空，后端会保留原密码
    }
    await settingsAPI.updateDatabaseConfig(dbData)
    
    ElMessage.success('设置已保存，重启应用后生效')
    visible.value = false
    
    // 刷新设置
    fundStore.loadAISettings()
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 插入变量
function insertVariable(variable, textareaId) {
  const textarea = document.getElementById(textareaId)
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = promptConfig.value[promptType.value][textareaId === 'user-prompt' ? 'user_prompt' : 'system_prompt']
    const newText = text.substring(0, start) + `{${variable}}` + text.substring(end)
    promptConfig.value[promptType.value][textareaId === 'user-prompt' ? 'user_prompt' : 'system_prompt'] = newText
  }
}

// 重置提示词
async function resetPrompts() {
  try {
    const result = await settingsAPI.resetPrompts()
    // 正确处理返回的提示词数据
    if (result && result.prompts) {
      promptConfig.value = {
        fund_analysis: {
          system_prompt: result.prompts.fund_analysis?.system_prompt || '',
          user_prompt: result.prompts.fund_analysis?.user_prompt || ''
        },
        portfolio_analysis: {
          system_prompt: result.prompts.portfolio_analysis?.system_prompt || '',
          user_prompt: result.prompts.portfolio_analysis?.user_prompt || ''
        }
      }
    }
    ElMessage.success('提示词已重置')
  } catch (error) {
    ElMessage.error(error.message || '重置失败')
  }
}

// 测试数据库连接
async function testDatabaseConnection() {
  testingConnection.value = true
  try {
    const result = await settingsAPI.testDatabaseConnection({
      db_type: dbConfig.value.type,
      sqlite_path: dbConfig.value.sqlite_path,
      pg_host: dbConfig.value.pg_host,
      pg_port: dbConfig.value.pg_port,
      pg_name: dbConfig.value.pg_name,
      pg_user: dbConfig.value.pg_user,
      pg_password: dbConfig.value.pg_password
    })
    
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error(error.message || '测试失败')
  } finally {
    testingConnection.value = false
  }
}

// 初始化数据库
async function initializeDatabase() {
  initializingDb.value = true
  try {
    const result = await settingsAPI.initializeDatabase({
      db_type: dbConfig.value.type,
      sqlite_path: dbConfig.value.sqlite_path,
      pg_host: dbConfig.value.pg_host,
      pg_port: dbConfig.value.pg_port,
      pg_name: dbConfig.value.pg_name,
      pg_user: dbConfig.value.pg_user,
      pg_password: dbConfig.value.pg_password
    })
    
    if (result.success) {
      ElMessage.success(result.message)
      // 刷新数据库状态
      const status = await settingsAPI.getDatabaseStatus()
      dbConnectionStatus.value = status
    } else {
      ElMessage.error(result.message || '初始化失败')
    }
  } catch (error) {
    ElMessage.error(error.message || '初始化失败')
  } finally {
    initializingDb.value = false
  }
}

// 选择 SQLite 文件（通过 input）
function selectSQLiteFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.db,.sqlite,.sqlite3'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (file) {
      // 使用相对路径
      dbConfig.value.sqlite_path = `./data/${file.name}`
    }
  }
  input.click()
}

// 创建新的 SQLite 数据库
function createNewSQLiteDb() {
  const timestamp = new Date().toISOString().slice(0, 10)
  dbConfig.value.sqlite_path = `./data/funds_${timestamp}.db`
  ElMessage.success('已生成新数据库路径，点击"初始化数据库"创建')
}

// 复制提示词
function copyPrompt(type) {
  const text = promptConfig.value[promptType.value][type === 'system' ? 'system_prompt' : 'user_prompt']
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}

onMounted(loadSettings)

watch(visible, (val) => {
  if (val) loadSettings()
})
</script>

<template>
  <el-drawer v-model="visible" title="设置" size="500px" direction="rtl">
    <el-tabs>
      <!-- 通用设置 -->
      <el-tab-pane label="📋 通用设置">
        <el-form label-width="100px">
          <el-form-item label="满仓金额">
            <el-input v-model="generalSettings.total_position_amount" placeholder="计划投资的总额">
              <template #prepend>¥</template>
            </el-input>
          </el-form-item>
          <div class="form-hint">用于计算当前仓位比例，辅助 AI 分析决策</div>
        </el-form>
      </el-tab-pane>

      <!-- AI 设置 -->
      <el-tab-pane label="🤖 AI 设置">
        <el-form label-width="100px">
          <el-form-item label="API Key">
            <div class="api-key-wrapper">
              <el-input v-model="aiSettings.api_key" type="password" show-password placeholder="sk-..." style="flex: 1" />
              <el-tag v-if="aiSettings.api_key_configured && !aiSettings.api_key" type="success" size="small">已配置</el-tag>
            </div>
            <div v-if="aiSettings.api_key_configured && !aiSettings.api_key" class="form-hint-inline">
              如需修改请输入新的 API Key，否则保持为空
            </div>
          </el-form-item>
          <el-form-item label="API 地址">
            <el-input v-model="aiSettings.base_url" placeholder="https://api.deepseek.com/v1" />
          </el-form-item>
          <el-form-item label="模型">
            <el-select v-model="aiSettings.model" style="width: 100%">
              <el-option value="deepseek-chat" label="deepseek-chat" />
              <el-option value="deepseek-coder" label="deepseek-coder" />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="form-hint">AI 设置将保存到项目根目录的 .env 文件中</div>
      </el-tab-pane>

      <!-- 数据库设置 -->
      <el-tab-pane label="💾 数据库设置">
        <!-- 数据库连接状态 -->
        <el-alert 
          v-if="dbConnectionStatus && dbConnectionStatus.connected" 
          type="success"
          :closable="false" 
          show-icon 
          style="margin-bottom: 16px"
        >
          <template #title>
            ✅ 数据库已连接
            <span style="margin-left: 8px; font-size: 12px; color: #909399;">
              ({{ dbConnectionStatus.total_tables || 0 }} 张表)
            </span>
          </template>
          <template v-if="dbConnectionStatus.database_type === 'sqlite'">
            路径: {{ dbConnectionStatus.path }}
          </template>
        </el-alert>
        
        <el-alert 
          v-else-if="dbConnectionStatus && !dbConnectionStatus.connected" 
          type="error"
          :closable="false" 
          show-icon 
          style="margin-bottom: 16px"
        >
          <template #title>❌ 数据库连接失败</template>
          <div style="font-size: 12px; margin-top: 4px;">{{ dbConnectionStatus.error || '无法连接到数据库' }}</div>
        </el-alert>
        
        <el-form label-width="100px">
          <el-form-item label="数据库类型">
            <el-radio-group v-model="dbConfig.type">
              <el-radio value="sqlite">SQLite（本地文件）</el-radio>
              <el-radio value="postgresql">PostgreSQL（服务器）</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <!-- SQLite 配置 -->
          <template v-if="dbConfig.type === 'sqlite'">
            <el-form-item label="数据文件">
              <div style="display: flex; gap: 8px;">
                <el-input v-model="dbConfig.sqlite_path" placeholder="./data/funds.db" style="flex: 1;" />
                <el-button @click="selectSQLiteFile">📁 选择</el-button>
                <el-button @click="createNewSQLiteDb">➕ 新建</el-button>
              </div>
              <div class="form-hint">支持 .db、.sqlite、.sqlite3 文件格式</div>
            </el-form-item>
          </template>
          
          <!-- PostgreSQL 配置 -->
          <template v-else>
            <el-form-item label="主机">
              <el-input v-model="dbConfig.pg_host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="dbConfig.pg_port" placeholder="5432" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="dbConfig.pg_name" placeholder="funds" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="dbConfig.pg_user" placeholder="postgres" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="dbConfig.pg_password" type="password" show-password placeholder="留空使用已保存的密码" />
              <div class="form-hint">如需修改密码请输入新密码，否则保持为空</div>
            </el-form-item>
          </template>
        </el-form>
        
        <!-- 操作按钮 -->
        <div style="display: flex; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid #e4e7ed;">
          <el-button 
            type="primary" 
            plain 
            @click="testDatabaseConnection"
            :loading="testingConnection"
          >
            🔌 测试连接
          </el-button>
          <el-button 
            type="success" 
            plain 
            @click="initializeDatabase"
            :loading="initializingDb"
          >
            🗄️ 初始化表结构
          </el-button>
        </div>
        
        <el-alert type="warning" :closable="false" style="margin-top: 16px">
          <template #title>⚠️ 注意</template>
          修改数据库配置后需要点击"保存设置"并重启应用才能生效
        </el-alert>
      </el-tab-pane>

      <!-- 提示词设置 -->
      <el-tab-pane label="📝 提示词设置">
        <el-tabs v-model="promptType">
          <el-tab-pane label="基金分析" name="fund">
            <div class="prompt-section">
              <div class="section-header">
                <span>系统提示词</span>
                <el-button size="small" text @click="copyPrompt('system')">复制</el-button>
              </div>
              <el-input
                id="system-prompt"
                v-model="promptConfig.fund_analysis.system_prompt"
                type="textarea"
                :rows="4"
                placeholder="系统提示词"
              />
            </div>
            
            <div class="prompt-section">
              <div class="section-header">
                <span>用户提示词</span>
                <el-button size="small" text @click="copyPrompt('user')">复制</el-button>
              </div>
              <el-input
                id="user-prompt"
                v-model="promptConfig.fund_analysis.user_prompt"
                type="textarea"
                :rows="8"
                placeholder="用户提示词"
              />
            </div>
            
            <div class="variables-section">
              <div class="section-header">可用变量（点击插入）</div>
              <div class="variable-tags">
                <el-tag v-for="v in fundVariables" :key="v.name" class="var-tag" @click="insertVariable(v.name, 'user-prompt')">
                  {{ v.name }} <span class="var-desc">{{ v.desc }}</span>
                </el-tag>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="持仓分析" name="portfolio">
            <div class="prompt-section">
              <div class="section-header">
                <span>系统提示词</span>
                <el-button size="small" text @click="copyPrompt('system')">复制</el-button>
              </div>
              <el-input
                v-model="promptConfig.portfolio_analysis.system_prompt"
                type="textarea"
                :rows="4"
                placeholder="系统提示词"
              />
            </div>
            
            <div class="prompt-section">
              <div class="section-header">
                <span>用户提示词</span>
                <el-button size="small" text @click="copyPrompt('user')">复制</el-button>
              </div>
              <el-input
                v-model="promptConfig.portfolio_analysis.user_prompt"
                type="textarea"
                :rows="8"
                placeholder="用户提示词"
              />
            </div>
            
            <div class="variables-section">
              <div class="section-header">可用变量（点击插入）</div>
              <div class="variable-tags">
                <el-tag v-for="v in portfolioVariables" :key="v.name" class="var-tag" @click="insertVariable(v.name, 'user-prompt')">
                  {{ v.name }} <span class="var-desc">{{ v.desc }}</span>
                </el-tag>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div class="prompt-actions">
          <el-button @click="resetPrompts">重置为默认</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="saveAllSettings">保存设置</el-button>
    </template>
  </el-drawer>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.form-hint-inline {
  font-size: 12px;
  color: #67c23a;
  margin-top: 4px;
}

.api-key-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.prompt-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 500;
  color: #303133;
}

.variables-section {
  margin-top: 16px;
}

.variable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.var-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.var-tag:hover {
  background: #409eff;
  color: #fff;
}

.var-desc {
  font-size: 11px;
  color: #909399;
  margin-left: 4px;
}

.var-tag:hover .var-desc {
  color: rgba(255, 255, 255, 0.8);
}

.prompt-actions {
  margin-top: 16px;
  text-align: center;
}
</style>
