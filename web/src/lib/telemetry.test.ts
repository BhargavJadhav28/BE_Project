import { describe, expect, it } from 'vitest';
import { generateScenarioData, SCENARIO_PRESETS } from './telemetry';

describe('Telemetry & Scenario Generator', () => {
	it('defines all 5 production presets', () => {
		expect(SCENARIO_PRESETS.length).toBe(5);
		const ids = SCENARIO_PRESETS.map((p) => p.id);
		expect(ids).toContain('summer-peak');
		expect(ids).toContain('winter-night');
		expect(ids).toContain('self-healing-gap');
	});

	it('generates 49 history steps and 24 forward weather steps', () => {
		const origin = '2026-06-15T12:00:00';
		const { history, weather } = generateScenarioData(origin);

		expect(history.length).toBe(49);
		expect(weather.length).toBe(24);

		// Assert chronological progression
		expect(history[0].timestamp < history[48].timestamp).toBe(true);
		expect(weather[0].timestamp < weather[23].timestamp).toBe(true);
	});

	it('strictly enforces solar night physics (0 GHI = 0 PV)', () => {
		const origin = '2026-12-18T18:00:00';
		const { history } = generateScenarioData(origin);

		// Midnight hour in history
		const midnight = history.find((h) => h.timestamp.endsWith('00:00:00'));
		expect(midnight).toBeDefined();
		if (midnight) {
			expect(midnight.ghi).toBe(0);
			expect(midnight.p_pv).toBe(0);
		}
	});

	it('injects sensor gap correctly when requested', () => {
		const origin = '2026-05-14T14:00:00';
		const { history } = generateScenarioData(origin, 2);

		// 49 - 2 = 47 rows
		expect(history.length).toBe(47);
	});
});
