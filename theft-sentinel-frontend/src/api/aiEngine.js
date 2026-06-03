import axiosInstance from './axios';

/**
 * AI Engine API Client
 * Handles all AI-related API calls for theft detection
 */

// Base path for AI endpoints
const AI_BASE = '/api/ai';

/**
 * Health Check - Check if AI service is ready
 * @returns {Promise} Health status
 */
export const getAIHealth = () => {
  return axiosInstance.get(`${AI_BASE}/health/`);
};

/**
 * Analyze Frame - Analyze a single frame for theft detection
 * @param {Object} data - Request data
 * @param {string} data.frame - Base64 encoded image
 * @param {string} [data.camera_id] - Optional camera ID
 * @param {boolean} [data.save_to_db=true] - Save inference to database
 * @param {boolean} [data.create_alert_on_theft=true] - Create alert if theft detected
 * @returns {Promise} Analysis response
 */
export const analyzeFrame = (data) => {
  return axiosInstance.post(`${AI_BASE}/analyze-frame/`, data);
};

/**
 * Process Camera - Capture and analyze frame from camera RTSP stream
 * @param {Object} data - Request data
 * @param {string} data.camera_id - Camera ID (required)
 * @param {boolean} [data.save_to_db=true] - Save inference to database
 * @param {boolean} [data.create_alert_on_theft=true] - Create alert if theft detected
 * @returns {Promise} Analysis response + camera metadata
 */
export const processCamera = (data) => {
  return axiosInstance.post(`${AI_BASE}/process-camera/`, data);
};

/**
 * Get Model Info - Get information about loaded AI models
 * @returns {Promise} Model information
 */
export const getModelInfo = () => {
  return axiosInstance.get(`${AI_BASE}/model-info/`);
};

/**
 * Get Inference History - Query historical inference results
 * @param {Object} params - Query parameters
 * @param {string} [params.camera_id] - Filter by camera
 * @param {string} [params.classification] - Filter by 'theft' or 'normal'
 * @param {number} [params.min_confidence] - Minimum confidence (0-1)
 * @param {number} [params.limit=50] - Max results (max 500)
 * @returns {Promise} Inference history
 */
export const getInferenceHistory = (params) => {
  return axiosInstance.get(`${AI_BASE}/inference-history/`, { params });
};

/**
 * Run Full Pipeline - Complete analysis pipeline (detection + pose + tracking + classification)
 * @param {Object} data - Request data (same as analyzeFrame)
 * @returns {Promise} Full pipeline response
 */
export const runFullPipeline = (data) => {
  return axiosInstance.post(`${AI_BASE}/full-pipeline/`, data);
};

/**
 * Start Continuous Monitoring - Start continuous monitoring for a camera
 * @param {string} cameraId - Camera ID to monitor
 * @returns {Promise} Start response
 */
export const startContinuousMonitoring = (cameraId) => {
  return axiosInstance.post(`${AI_BASE}/monitor/start/`, { camera_id: cameraId });
};

/**
 * Get Monitor Status - Get real-time status of continuous monitoring
 * @param {string} cameraId - Camera ID
 * @returns {Promise} Monitor status with latest results
 */
export const getMonitorStatus = (cameraId) => {
  return axiosInstance.get(`${AI_BASE}/monitor/status/`, { params: { camera_id: cameraId } });
};

/**
 * Stop Continuous Monitoring - Stop continuous monitoring for a camera
 * @param {string} cameraId - Camera ID to stop
 * @returns {Promise} Stop response
 */
export const stopContinuousMonitoring = (cameraId) => {
  return axiosInstance.post(`${AI_BASE}/monitor/stop/`, { camera_id: cameraId });
};

