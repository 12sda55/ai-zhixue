/**
 * ECharts 图表导出为 base64 图片
 */

import * as echarts from 'echarts/core'
import { RadarChart as RadarChartSeries } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProfileData, ProfileAllDimensionKey } from '../../../shared/types'
import { DIMENSION_META } from '../../../shared/types'

echarts.use([RadarChartSeries, TooltipComponent, LegendComponent, CanvasRenderer])

/** 导出雷达图为 base64 */
export function exportRadarChart(profileData: ProfileData): string {
  const div = document.createElement('div')
  div.style.width = '400px'
  div.style.height = '400px'
  div.style.position = 'absolute'
  div.style.left = '-9999px'
  document.body.appendChild(div)

  const chart = echarts.init(div, undefined, { renderer: 'canvas' })

  // 只取雷达图上显示的维度
  const radarDims = profileData.dimensions.filter(d => d.showOnRadar !== false)
  const indicator = radarDims.map(d => ({
    name: `${DIMENSION_META[d.key as ProfileAllDimensionKey]?.icon || ''} ${d.name}`,
    max: 100,
  }))
  const values = radarDims.map(d => d.value)

  chart.setOption({
    radar: { indicator, shape: 'polygon', radius: '65%' },
    series: [{
      type: 'radar',
      data: [{ value: values, name: '当前', areaStyle: { color: 'rgba(0,212,255,0.2)' }, lineStyle: { color: '#00d4ff' } }],
    }],
  })

  const base64 = chart.getDataURL({ pixelRatio: 2, backgroundColor: '#fff' })
  chart.dispose()
  document.body.removeChild(div)
  return base64
}
