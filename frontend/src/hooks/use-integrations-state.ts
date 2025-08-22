import { useReducer, useCallback } from 'react'

// Types
interface Integration {
  id: number
  platform: string
  name: string
  configuration: any
  status: string
  created_at: string
  updated_at: string
  last_sync?: string
  sync_status?: string
  error_message?: string
}

interface GitHubIntegration {
  id: number
  user_id: number
  github_token_suffix: string
  github_username: string
  github_organization: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
}

interface SlackIntegration {
  id: number
  user_id: number
  team_id: string
  team_name: string
  webhook_url_suffix: string
  bot_token_suffix: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
}

interface IntegrationsState {
  // Data
  integrations: Integration[]
  githubIntegration: GitHubIntegration | null
  slackIntegration: SlackIntegration | null
  userInfo: {name: string, email: string, avatar?: string} | null
  
  // Loading states (consolidated)
  loading: {
    rootly: boolean
    pagerDuty: boolean
    github: boolean
    slack: boolean
    mappingData: boolean
    refreshing: boolean
  }
  
  // UI states (consolidated)
  ui: {
    activeTab: "rootly" | "pagerduty" | null
    backUrl: string
    selectedOrganization: string
    activeEnhancementTab: "github" | "slack" | null
    addingPlatform: "rootly" | "pagerduty" | null
    editingIntegration: number | null
    editingName: string
  }
  
  // Modal/Dialog states (consolidated)
  dialogs: {
    showMappingDialog: boolean
    selectedMappingPlatform: 'github' | 'slack' | null
    mappingDrawerOpen: boolean
    mappingDrawerPlatform: 'github' | 'slack'
    showManualMappingDialog: boolean
    newMappingDialogOpen: boolean
    githubDisconnectDialogOpen: boolean
    slackDisconnectDialogOpen: boolean
    deleteDialogOpen: boolean
    showGithubInstructions: boolean
    showSlackInstructions: boolean
    showRootlyInstructions: boolean
    showPagerDutyInstructions: boolean
  }
  
  // Form states (consolidated)
  forms: {
    githubToken: string
    slackWebhookUrl: string
    slackBotToken: string
    llmToken: string
    llmModel: string
    llmProvider: string
    showGithubToken: boolean
    showSlackWebhook: boolean
    showSlackToken: boolean
    showLlmToken: boolean
  }
  
  // Status states (consolidated)
  status: {
    refreshingInBackground: boolean
    isConnectingGithub: boolean
    isConnectingSlack: boolean
    isDisconnectingGithub: boolean
    isDisconnectingSlack: boolean
    isDeleting: boolean
    validatingGithub: boolean
    githubValidation: {valid: boolean, message?: string} | null
    connectionStatus: 'idle' | 'success' | 'error' | 'duplicate'
    isTestingConnection: boolean
    copied: boolean
  }
}

// Action types
type IntegrationsAction =
  | { type: 'SET_INTEGRATIONS'; payload: Integration[] }
  | { type: 'SET_GITHUB_INTEGRATION'; payload: GitHubIntegration | null }
  | { type: 'SET_SLACK_INTEGRATION'; payload: SlackIntegration | null }
  | { type: 'SET_USER_INFO'; payload: IntegrationsState['userInfo'] }
  | { type: 'SET_LOADING'; payload: Partial<IntegrationsState['loading']> }
  | { type: 'SET_UI'; payload: Partial<IntegrationsState['ui']> }
  | { type: 'SET_DIALOGS'; payload: Partial<IntegrationsState['dialogs']> }
  | { type: 'SET_FORMS'; payload: Partial<IntegrationsState['forms']> }
  | { type: 'SET_STATUS'; payload: Partial<IntegrationsState['status']> }
  | { type: 'RESET_STATE' }

// Initial state
const initialState: IntegrationsState = {
  integrations: [],
  githubIntegration: null,
  slackIntegration: null,
  userInfo: null,
  
  loading: {
    rootly: true,
    pagerDuty: true,
    github: true,
    slack: true,
    mappingData: false,
    refreshing: false
  },
  
  ui: {
    activeTab: null,
    backUrl: '/dashboard',
    selectedOrganization: '',
    activeEnhancementTab: null,
    addingPlatform: null,
    editingIntegration: null,
    editingName: ''
  },
  
  dialogs: {
    showMappingDialog: false,
    selectedMappingPlatform: null,
    mappingDrawerOpen: false,
    mappingDrawerPlatform: 'github',
    showManualMappingDialog: false,
    newMappingDialogOpen: false,
    githubDisconnectDialogOpen: false,
    slackDisconnectDialogOpen: false,
    deleteDialogOpen: false,
    showGithubInstructions: false,
    showSlackInstructions: false,
    showRootlyInstructions: false,
    showPagerDutyInstructions: false
  },
  
  forms: {
    githubToken: '',
    slackWebhookUrl: '',
    slackBotToken: '',
    llmToken: '',
    llmModel: 'gpt-4o-mini',
    llmProvider: 'openai',
    showGithubToken: false,
    showSlackWebhook: false,
    showSlackToken: false,
    showLlmToken: false
  },
  
  status: {
    refreshingInBackground: false,
    isConnectingGithub: false,
    isConnectingSlack: false,
    isDisconnectingGithub: false,
    isDisconnectingSlack: false,
    isDeleting: false,
    validatingGithub: false,
    githubValidation: null,
    connectionStatus: 'idle',
    isTestingConnection: false,
    copied: false
  }
}

// Reducer
function integrationsReducer(state: IntegrationsState, action: IntegrationsAction): IntegrationsState {
  switch (action.type) {
    case 'SET_INTEGRATIONS':
      return { ...state, integrations: action.payload }
    case 'SET_GITHUB_INTEGRATION':
      return { ...state, githubIntegration: action.payload }
    case 'SET_SLACK_INTEGRATION':
      return { ...state, slackIntegration: action.payload }
    case 'SET_USER_INFO':
      return { ...state, userInfo: action.payload }
    case 'SET_LOADING':
      return { ...state, loading: { ...state.loading, ...action.payload } }
    case 'SET_UI':
      return { ...state, ui: { ...state.ui, ...action.payload } }
    case 'SET_DIALOGS':
      return { ...state, dialogs: { ...state.dialogs, ...action.payload } }
    case 'SET_FORMS':
      return { ...state, forms: { ...state.forms, ...action.payload } }
    case 'SET_STATUS':
      return { ...state, status: { ...state.status, ...action.payload } }
    case 'RESET_STATE':
      return initialState
    default:
      return state
  }
}

// Custom hook
export function useIntegrationsState() {
  const [state, dispatch] = useReducer(integrationsReducer, initialState)
  
  // Action creators
  const setIntegrations = useCallback((integrations: Integration[]) => {
    dispatch({ type: 'SET_INTEGRATIONS', payload: integrations })
  }, [])
  
  const setGithubIntegration = useCallback((integration: GitHubIntegration | null) => {
    dispatch({ type: 'SET_GITHUB_INTEGRATION', payload: integration })
  }, [])
  
  const setSlackIntegration = useCallback((integration: SlackIntegration | null) => {
    dispatch({ type: 'SET_SLACK_INTEGRATION', payload: integration })
  }, [])
  
  const setUserInfo = useCallback((userInfo: IntegrationsState['userInfo']) => {
    dispatch({ type: 'SET_USER_INFO', payload: userInfo })
  }, [])
  
  const setLoading = useCallback((loading: Partial<IntegrationsState['loading']>) => {
    dispatch({ type: 'SET_LOADING', payload: loading })
  }, [])
  
  const setUI = useCallback((ui: Partial<IntegrationsState['ui']>) => {
    dispatch({ type: 'SET_UI', payload: ui })
  }, [])
  
  const setDialogs = useCallback((dialogs: Partial<IntegrationsState['dialogs']>) => {
    dispatch({ type: 'SET_DIALOGS', payload: dialogs })
  }, [])
  
  const setForms = useCallback((forms: Partial<IntegrationsState['forms']>) => {
    dispatch({ type: 'SET_FORMS', payload: forms })
  }, [])
  
  const setStatus = useCallback((status: Partial<IntegrationsState['status']>) => {
    dispatch({ type: 'SET_STATUS', payload: status })
  }, [])
  
  const resetState = useCallback(() => {
    dispatch({ type: 'RESET_STATE' })
  }, [])
  
  return {
    // State
    ...state,
    
    // Actions
    setIntegrations,
    setGithubIntegration,
    setSlackIntegration,
    setUserInfo,
    setLoading,
    setUI,
    setDialogs,
    setForms,
    setStatus,
    resetState
  }
}