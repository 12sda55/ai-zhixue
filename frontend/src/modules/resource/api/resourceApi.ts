import request from '../../../shared/utils/request'

export function getList() {
  return request.get('/data/resources')
}

export function getDetail(id: string) {
  return request.get(`/resource/detail/${id}`)
}