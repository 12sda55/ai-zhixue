import request from '../../../shared/utils/request'

export function getPlan() {
  return request.get('/path/plan')
}