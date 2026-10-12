import type { HistoricalReading, ScenarioPreset, WeatherForecastStep } from './types';

export const SCENARIO_PRESETS: ScenarioPreset[] = [
	{
		id: 'summer-peak',
		name: 'Summer Solar Peak',
		description: 'Sunny summer day. Solar generation exceeds 40 kW at noon. Afternoon cooling increases building demand.',
		origin: '2026-06-15T12:00:00',
		season: 'summer'
	},
	{
		id: 'spring-ramp',
		name: 'Spring Dynamic Dispatch',
		description: 'Mild spring morning. Solar power rises quickly while commercial building equipment turns on.',
		origin: '2026-03-20T08:00:00',
		season: 'spring'
	},
	{
		id: 'winter-night',
		name: 'Winter Evening Peak',
		description: 'Cold winter evening. Solar generation is 0.0 kW while heating creates peak power demand.',
		origin: '2026-12-18T18:00:00',
		season: 'winter'
	},
	{
		id: 'cloud-storm',
		name: 'Storm Front Intermittency',
		description: 'Passing storm front. Rapid cloud cover changes cause sudden drops in solar generation.',
		origin: '2026-09-10T11:00:00',
		season: 'autumn'
	},
	{
		id: 'self-healing-gap',
		name: 'Self-Healing Gap Test (2h Drop)',
		description: 'Simulates a 2-hour sensor signal loss. The pipeline fills missing values automatically.',
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
	// Solar geometry for Pune microgrid (18.55°N)
	const delta = (23.45 * Math.PI / 180) * Math.sin((2 * Math.PI * (284 + dayOfYear)) / 365.25);
	const omega = (15 * Math.PI / 180) * (hour - 12);
	const phi = (18.55 * Math.PI / 180);

	let cosZenith = Math.sin(phi) * Math.sin(delta) + Math.cos(phi) * Math.cos(delta) * Math.cos(omega);
	cosZenith = Math.max(0, cosZenith);

	const clearSky = cosZenith > 0 ? 1050 * Math.pow(cosZenith, 1.15) : 0;
	// Seasonal monsoon cloud modifier (June - August: days 160 to 260)
	const monsoonCloud = (dayOfYear >= 160 && dayOfYear <= 260) ? 35 : 0;
	const cloud = Math.min(100, Math.max(0, 18 + 10 * Math.sin(hour / 3.5) + monsoonCloud));
	const ghi = clearSky * (1 - 0.75 * (cloud / 100));

	// Ambient Temperature calibrated to Pune climate (12.0°C to 43.5°C)
	const seasonalTemp = 24.0 + 7.5 * Math.sin((2 * Math.PI * (dayOfYear - 75)) / 365.25);
	const diurnalTemp = (8.0 - 2.5 * (cloud / 100)) * Math.cos((2 * Math.PI * (hour - 15)) / 24);
	const monsoonCooling = (dayOfYear >= 160 && dayOfYear <= 260) ? -3.5 * (cloud / 100) : 0;
	const temp = Math.round((seasonalTemp + diurnalTemp + monsoonCooling) * 10) / 10;

	return { ghi: Math.max(0, ghi), temp, cloud };
}

function computePowerPhysics(ghi: number, temp: number, cloud: number, hour: number, isWeekend: boolean) {
	// 50 kW peak PV with thermal derating and inverter efficiency
	let derating = 1 - 0.004 * (temp - 25);
	derating = Math.max(0.7, Math.min(1.1, derating));

	const pDc = 50.0 * (ghi / 1000) * derating;
	// Sandia inverter conversion loss
	const pLoss = pDc > 0.10 ? (0.10 + 0.018 * pDc + 0.0004 * (pDc * pDc)) : pDc;
	// Apply 1.25x presentation surplus factor clipped to 50 kW inverter rating
	let pPv = Math.max(0, pDc - pLoss) * 1.25;
	if (ghi <= 0) pPv = 0;
	pPv = Math.max(0, Math.min(50.0, pPv));

	// Commercial facility load demand with Pune HVAC thermal response
	const diurnalCurve = [
		0.05, 0.03, 0.02, 0.02, 0.03, 0.06,
		0.25, 0.50, 0.68, 0.75,
		0.78, 0.80, 0.76, 0.75, 0.78, 0.82, 0.85, 0.88,
		0.95, 1.00, 0.98, 0.88, 0.70, 0.40
	];
	const factor = diurnalCurve[hour % 24];
	const weekendDiscount = isWeekend ? 0.82 : 1.0;
	// HVAC cooling kicks in strongly above 24°C
	const coolingLoad = Math.max(0, temp - 24.0) * 0.70;
	const heatingLoad = Math.max(0, 16.0 - temp) * 0.35;
	const hvac = coolingLoad + heatingLoad;

	let pLoad = 10.0 + (30.0 * factor * weekendDiscount) + hvac;
	pLoad = Math.max(10.0, Math.min(54.0, pLoad));

	return { p_pv: Math.round(pPv * 100) / 100, p_load: Math.round(pLoad * 100) / 100 };
}

/**
 * Fetch live real-time weather and 24-hour forward forecast for Pune (18.55°N, 73.85°E) from Open-Meteo.
 * Falls back to offline physics generation if the network is unavailable or date is outside the live window.
 */
export async function getTelemetryData(
	originStr: string,
	injectGapHours: number = 0
): Promise<{ history: HistoricalReading[]; weather: WeatherForecastStep[]; isLiveWeather: boolean }> {
	try {
		const targetDate = new Date(originStr.endsWith('Z') ? originStr : originStr + 'Z');
		const now = new Date();
		const diffHours = Math.abs(targetDate.getTime() - now.getTime()) / (3600 * 1000);

		// If date is within 48h of now, query live Open-Meteo API
		if (diffHours <= 48) {
			const res = await fetch(
				'https://api.open-meteo.com/v1/forecast?latitude=18.55&longitude=73.85&hourly=temperature_2m,shortwave_radiation,cloud_cover&past_days=2&forecast_days=2&timezone=auto',
				{ signal: AbortSignal.timeout(3500) }
			);

			if (res.ok) {
				const json = await res.json();
				const times: string[] = json.hourly?.time || [];
				const temps: number[] = json.hourly?.temperature_2m || [];
				const ghis: number[] = json.hourly?.shortwave_radiation || [];
				const clouds: number[] = json.hourly?.cloud_cover || [];

				// Match origin hour
				const originPrefix = originStr.slice(0, 13); // "YYYY-MM-DDTHH"
				let originIdx = times.findIndex((t) => t.startsWith(originPrefix));

				if (originIdx >= 48 && originIdx + 24 <= times.length) {
					const history: HistoricalReading[] = [];
					const weather: WeatherForecastStep[] = [];

					// 49 historical hours [-48h .. T]
					for (let i = 48; i >= 0; i--) {
						const idx = originIdx - i;
						const iso = times[idx] ? times[idx] + ':00' : '';
						const date = new Date(iso);
						const hour = date.getHours();
						const isWeekend = date.getDay() === 0 || date.getDay() === 6;

						if (injectGapHours > 0 && i >= 6 && i < 6 + injectGapHours) {
							continue;
						}

						const ghi = Math.max(0, ghis[idx] || 0);
						const temp = temps[idx] || 25;
						const cloud = Math.min(100, Math.max(0, clouds[idx] || 0));
						const { p_pv, p_load } = computePowerPhysics(ghi, temp, cloud, hour, isWeekend);

						history.push({
							timestamp: iso,
							ghi: Math.round(ghi * 10) / 10,
							temp_amb: Math.round(temp * 10) / 10,
							cloud_cover: Math.round(cloud * 10) / 10,
							p_pv,
							p_load
						});
					}

					// 24 forward weather forecast hours [T+1h .. T+24h]
					for (let h = 1; h <= 24; h++) {
						const idx = originIdx + h;
						const iso = times[idx] ? times[idx] + ':00' : '';
						const ghi = Math.max(0, ghis[idx] || 0);
						const temp = temps[idx] || 25;
						const cloud = Math.min(100, Math.max(0, clouds[idx] || 0));

						weather.push({
							timestamp: iso,
							ghi: Math.round(ghi * 10) / 10,
							temp_amb: Math.round(temp * 10) / 10,
							cloud_cover: Math.round(cloud * 10) / 10
						});
					}

					return { history, weather, isLiveWeather: true };
				}
			}
		}
	} catch (e) {
		console.warn('Live Open-Meteo fetch failed or offline; using calibrated Pune simulation:', e);
	}

	// Offline or historical scenario fallback
	const { history, weather } = generateScenarioData(originStr, injectGapHours);
	return { history, weather, isLiveWeather: false };
}

