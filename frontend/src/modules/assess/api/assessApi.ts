import request from '../../../shared/utils/request'

export function getReport() {
  return request.get('/assess/report')
}

// P0优化：学习效果评估API
export function getLearningEffect() {
  return request.get('/assess/learning-effect')
}