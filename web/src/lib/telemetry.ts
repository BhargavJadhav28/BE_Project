import type { HistoricalReading, ScenarioPreset, WeatherForecastStep } from './types';

export const SCENARIO_PRESETS: ScenarioPreset[] = [
	{
		id: 'summer-peak',
		name: 'Summer Solar Peak',
		description: 'Clear sunny summer day with 40+ kW midday solar generation and high afternoon cooling load.',
		origin: '2026-06-15T12:00:00',
		season: 'summer'
	},
	{
		id: 'spring-ramp',
		name: 'Spring Dynamic Dispatch',
		description: 'Mild spring morning with rapidly rising solar irradiance and industrial commercial startup ramp.',
		origin: '2026-03-20T08:00:00',
		season: 'spring'
	},
	{
		id: 'winter-night',
		name: 'Winter Evening Peak',
		description: 'Chilly winter evening with 0 kW nocturnal solar generation and peak residential heating demand.',
		origin: '2026-12-18T18:00:00',
		season: 'winter'
	},
	{
		id: 'cloud-storm',
		name: 'Storm Front Intermittency',
		description: 'Passing storm front with sudden 80% cloud cover dropouts and erratic irradiance spikes.',
		origin: '2026-09-10T11:00:00',
		season: 'autumn'
	},
	{
		id: 'self-healing-gap',
		name: 'Self-Healing Gap Test (2h Drop)',
		description: 'Simulates a 2-hour sensor packet loss. Verifies linear gap interpolation and nocturnal zero-fill.',
		origin: '2026-05-14T14:00:00',
		season: 'spring',
		hasGap: true,
		gapHours: 2
	}
];

/**
 * Generate 48h history and 24h weather forecast aligned to the specified origin.
 */
export function generateScenarioData(
	originStr: string,
	injectGapHours: number = 0
): { history: HistoricalReading[]; weather: WeatherForecastStep[] } {
	const originDate = new Date(originStr.endsWith('Z') ? originStr : originStr + 'Z');
	const history: HistoricalReading[] = [];
	const weather: WeatherForecastStep[] = [];

	// 1. Generate 49 hourly points for history [-48h .. T]
	for (let i = 48; i >= 0; i--) {
		const stepDate = new Date(originDate.getTime() - i * 3600 * 1000);
		const iso = stepDate.toISOString().slice(0, 19);

		const hour = stepDate.getUTCHours();
		const dayOfYear = getDayOfYear(stepDate);
		const isWeekend = stepDate.getUTCDay() === 0 || stepDate.getUTCDay() === 6;

		// Skip rows to simulate sensor drop if requested
		if (injectGapHours > 0 && i >= 6 && i < 6 + injectGapHours) {
			continue;
		}

		const { ghi, temp, cloud } = computeWeatherPhysics(hour, dayOfYear);
		const { p_pv, p_load } = computePowerPhysics(ghi, temp, cloud, hour, isWeekend);

		history.push({
			timestamp: iso,
			ghi: Math.round(ghi * 10) / 10,
			temp_amb: Math.round(temp * 10) / 10,
			cloud_cover: Math.round(cloud * 10) / 10,
			p_pv: Math.round(p_pv * 100) / 100,
			p_load: Math.round(p_load * 100) / 100
		});
	}

	// 2. Generate 24 hourly points for future weather [T+1h .. T+24h]
	for (let h = 1; h <= 24; h++) {
		const stepDate = new Date(originDate.getTime() + h * 3600 * 1000);
		const iso = stepDate.toISOString().slice(0, 19);

		const hour = stepDate.getUTCHours();
		const dayOfYear = getDayOfYear(stepDate);

		const { ghi, temp, cloud } = computeWeatherPhysics(hour, dayOfYear);

		weather.push({
			timestamp: iso,
			ghi: Math.round(ghi * 10) / 10,
			temp_amb: Math.round(temp * 10) / 10,
			cloud_cover: Math.round(cloud * 10) / 10
		});
	}

	return { history, weather };
}

function getDayOfYear(date: Date): number {
	const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0));
	const diff = date.getTime() - start.getTime();
	return Math.floor(diff / (1000 * 60 * 60 * 24));
}

function computeWeatherPhysics(hour: number, dayOfYear: number) {
	// Solar geometry
	const delta = (23.45 * Math.PI / 180) * Math.sin((2 * Math.PI * (284 + dayOfYear)) / 365.25);
	const omega = (15 * Math.PI / 180) * (hour - 12);
	const phi = (25 * Math.PI / 180);

	let cosZenith = Math.sin(phi) * Math.sin(delta) + Math.cos(phi) * Math.cos(delta) * Math.cos(omega);
	cosZenith = Math.max(0, cosZenith);

	const clearSky = cosZenith > 0 ? 1000 * Math.pow(cosZenith, 1.15) : 0;
	const cloud = 20 + 15 * Math.sin(hour / 3.5);
	const ghi = clearSky * (1 - 0.75 * (cloud / 100));

	const seasonalTemp = 18 + 14 * Math.sin((2 * Math.PI * (dayOfYear - 105)) / 365.25);
	const diurnalTemp = 7 * Math.cos((2 * Math.PI * (hour - 15)) / 24);
	const temp = seasonalTemp + diurnalTemp;

	return { ghi: Math.max(0, ghi), temp, cloud: Math.min(100, Math.max(0, cloud)) };
}

function computePowerPhysics(ghi: number, temp: number, cloud: number, hour: number, isWeekend: boolean) {
	// 50 kW peak PV with thermal derating
	let derating = 1 - 0.004 * (temp - 25);
	derating = Math.max(0.7, Math.min(1.1, derating));

	let p_pv = 50.0 * (ghi / 1000) * derating;
	if (ghi <= 0) p_pv = 0;
	p_pv = Math.max(0, Math.min(50.0, p_pv));

	// Load demand with dual peak
	const diurnalCurve = [
		0.28, 0.25, 0.24, 0.24, 0.26, 0.32,
		0.50, 0.75, 0.85, 0.78, 0.72, 0.70,
		0.68, 0.67, 0.69, 0.72, 0.76, 0.82,
		0.95, 1.00, 0.92, 0.78, 0.55, 0.38
	];
	const factor = diurnalCurve[hour % 24];
	const weekendDiscount = isWeekend ? 0.82 : 1.0;
	const hvac = Math.max(0, temp - 22) * 0.45 + Math.max(0, 16 - temp) * 0.35;

	let p_load = 10.0 + (30.0 * factor * weekendDiscount) + hvac;
	p_load = Math.max(10.0, Math.min(45.0, p_load));

	return { p_pv, p_load };
}
