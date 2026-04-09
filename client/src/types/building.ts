export interface Building {
  id: string
  name: string
  type: string
  address?: string
}

export interface Floor {
  id: string
  building_id: string
  floor_number: number
  floor_name: string
  image_url: string
  width: number
  height: number
  created_at?: string
}

export interface Space {
  id: string
  floor_id: string
  space_type: 'room' | 'area'
  name: string
  code: string
  polygon: number[][]
  center_x: number
  center_y: number
  area_sqm: number
  energy_per_sqm?: number
  created_at?: string
}

export interface MeterBinding {
  meter_id: string
  space_id: string
  building_id?: string
  type?: string
  status?: string
}
