/**
 * Global AI Monitoring State — Recoil atomFamily
 *
 * One atom per camera ID.  Because atoms live inside <RecoilRoot> (which wraps
 * the entire app), their values survive component unmounts.  Navigating from
 * the Control Room to Alerts and back never resets the monitoring state.
 *
 * Usage:
 *   import { cameraMonitoringState } from '../../store/monitoringStore';
 *   const [isMonitoring, setIsMonitoring] =
 *     useRecoilState(cameraMonitoringState(String(cameraId)));
 */
import { atomFamily } from 'recoil';

export const cameraMonitoringState = atomFamily({
  key:     'cameraMonitoringState',
  default: false,          // each camera starts as "not monitoring"
});
