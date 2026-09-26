export interface HistoricalReading {
	timestamp: string;
	ghi: number;
	temp_amb: number;
	cloud_cover: number;
	p_pv: number;
	p_load: number;
}

export interface WeatherForecastStep {
	timestamp: string;
	ghi: number;
	temp_amb: number;
	cloud_cover: number;
}

export interface ForecastRequest {
	origin: string;
	history: HistoricalReading[];
	weather_forecast: WeatherForecastStep[];
}

export interface ForecastMetadata {
	origin: string;
	execution_time_ms: number;
}

export interface ForecastResponse {
	timestamps: string[];
	p_pv_forecast: number[];
	p_load_forecast: number[];
	metadata: ForecastMetadata;
}

export interface BackendHealth {
	status: 'healthy' | 'offline' | 'checking';
	service?: string;
	manifest?: string;
	error?: string;
}

export interface ScenarioPreset {
	id: string;
	name: string;
	description: string;
	origin: string;
	season: string;
	hasGap?: boolean;
	gapHours?: number;
}
