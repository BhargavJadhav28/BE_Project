<script lang="ts">
	import type { HistoricalReading, WeatherForecastStep } from '../types';

	interface Props {
		history: HistoricalReading[];
		weather: WeatherForecastStep[];
	}

	let { history = [], weather = [] }: Props = $props();

	type TabId = 'weather' | 'history' | 'specs' | 'parameters';
	let activeTab = $state<TabId>('weather');
</script>

<div class="drawer-panel">
	<!-- Tab Bar -->
	<div class="drawer-tabs">
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'weather'}
			onclick={() => (activeTab = 'weather')}
		>Forward weather ({weather.length}h)</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'history'}
			onclick={() => (activeTab = 'history')}
		>Sensor history ({history.length}h)</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'specs'}
			onclick={() => (activeTab = 'specs')}
		>Architecture & SLA</button>
		<button
			class="tab-btn font-mono"
			class:active={activeTab === 'parameters'}
			onclick={() => (activeTab = 'parameters')}
		>Parameters & units</button>
	</div>

	<!-- Content Body -->
	<div class="drawer-body">
		{#if activeTab === 'weather'}
			<div class="table-container font-mono">
				<table class="data-table">
					<thead>
						<tr>
							<th>Horizon</th>
							<th>Target timestamp</th>
							<th>Irradiance (GHI)</th>
							<th>Temperature</th>
							<th>Cloud cover</th>
							<th>State</th>
						</tr>
					</thead>
					<tbody>
						{#each weather as row, i}
							<tr>
								<td class="horizon-cell">T+{i + 1}</td>
								<td class="time-cell">{row.timestamp.replace('T', ' ')}</td>
								<td>
									<div class="cell-with-bar">
										<span class="pv-text">{row.ghi.toFixed(1)} W/m²</span>
										<div class="bar-track">
											<div class="bar-fill pv-fill" style="width: {Math.min(100, (row.ghi / 1000) * 100)}%;"></div>
										</div>
									</div>
								</td>
								<td>{row.temp_amb.toFixed(1)} °C</td>
								<td>
									<div class="cell-with-bar">
										<span>{row.cloud_cover.toFixed(0)}%</span>
										<div class="bar-track">
											<div class="bar-fill cloud-fill" style="width: {row.cloud_cover}%;"></div>
										</div>
									</div>
								</td>
								<td>
									{#if row.ghi > 0}
										<span class="status-tag daylight">Daylight</span>
									{:else}
										<span class="status-tag night">Nocturnal</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else if activeTab === 'history'}
			<div class="table-container font-mono">
				<table class="data-table">
					<thead>
						<tr>
							<th>Lag step</th>
							<th>Timestamp</th>
							<th>Solar generation</th>
							<th>Facility load</th>
							<th>Irradiance (GHI)</th>
							<th>Temperature</th>
						</tr>
					</thead>
					<tbody>
						{#each history.slice(-25) as row, i}
							{@const lagHours = 24 - i}
							<tr>
								<td class="horizon-cell">{lagHours === 0 ? 'T (Origin)' : `T-${lagHours}h`}</td>
								<td class="time-cell">{row.timestamp.replace('T', ' ')}</td>
								<td class="pv-text font-bold">{row.p_pv.toFixed(2)} kW</td>
								<td class="load-text font-bold">{row.p_load.toFixed(2)} kW</td>
								<td>{row.ghi.toFixed(1)} W/m²</td>
								<td>{row.temp_amb.toFixed(1)} °C</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else if activeTab === 'specs'}
			<div class="specs-grid">
				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">Physical asset envelope</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">PV Inverter ceiling</span>
							<span class="spec-val pv-text">50.0 kW</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Peak load demand</span>
							<span class="spec-val load-text">45.0 kW</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Overnight baseload</span>
							<span class="spec-val">10.0 kW</span>
						</div>
					</div>
				</div>

				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">Model architecture</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">Regressor type</span>
							<span class="spec-val">Dual LightGBM</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Conditioning</span>
							<span class="spec-val">Horizon index h ∈ [1..24]</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Hyperparameters</span>
							<span class="spec-val">150 trees, max depth 6</span>
						</div>
					</div>
				</div>

				<div class="spec-card">
					<div class="spec-card-head">
						<h3 class="spec-card-title">4-Season SLA benchmarks</h3>
					</div>
					<div class="spec-rows font-mono">
						<div class="spec-item">
							<span class="spec-lbl">PV Daylight nMAE</span>
							<span class="spec-val surplus-text">0.26% (SLA ≤ 5.0%)</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Load 24h nMAE</span>
							<span class="spec-val surplus-text">2.99% (SLA ≤ 6.0%)</span>
						</div>
						<div class="spec-item">
							<span class="spec-lbl">Variance explained (R²)</span>
							<span class="spec-val surplus-text">&gt; 0.93 (SLA ≥ 0.85)</span>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="params-grid">
				<div class="param-box">
					<span class="param-category font-mono">Operator control</span>
					<h3 class="param-name">Forecast origin timestamp (T)</h3>
					<p class="param-description">The temporal anchor for decision making. History lookback covers [T-48h..T]; forecasts project forward [T+1h..T+24h].</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Weather input</span>
					<h3 class="param-name">Global horizontal irradiance (GHI)</h3>
					<p class="param-description">Total solar radiation per square meter (W/m²). Directly dictates solar generation and is strictly zero during nighttime.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Weather input</span>
					<h3 class="param-name">Ambient temperature (°C)</h3>
					<p class="param-description">Outside temperature. Influences building HVAC demand and solar panel thermal efficiency derating.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Model output</span>
					<h3 class="param-name">Solar PV power (P̂_pv)</h3>
					<p class="param-description">Predicted generation bounded by [0..50 kW] inverter limit and enforced with hard zeroing during nocturnal intervals.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Model output</span>
					<h3 class="param-name">Building load demand (P̂_load)</h3>
					<p class="param-description">Predicted electrical consumption between 10 kW baseload and 45 kW peak, capturing facility work and occupancy schedules.</p>
				</div>

				<div class="param-box">
					<span class="param-category font-mono">Energy balance</span>
					<h3 class="param-name">Net power & storage arbitrage</h3>
					<p class="param-description">Instantaneous difference P̂_net = P̂_pv − P̂_load. Positive energy charges battery storage; negative energy draws battery or grid power.</p>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.drawer-panel {
		background: #09090C;
		border: 1px solid #1C1C24;
		border-radius: 8px;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.drawer-tabs {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 10px 1.5rem;
		background: #050507;
		border-bottom: 1px solid #1C1C24;
		overflow-x: auto;
	}

	.tab-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: 32px;
		padding: 0 14px;
		background: transparent;
		color: #71717A;
		font-family: inherit;
		font-size: 0.775rem;
		font-weight: 500;
		line-height: 1;
		cursor: pointer;
		white-space: nowrap;
		border-radius: 6px;
		border: 1px solid transparent;
		box-sizing: border-box;
		transition: all 0.15s ease;
	}

	.tab-btn:hover {
		color: #FFFFFF;
		background: #141418;
	}

	.tab-btn.active {
		background: #1C1C24;
		border-color: #2E2E38;
		color: #FFFFFF;
	}

	.drawer-body {
		padding: 1.5rem 1.75rem;
		background: #09090C;
	}

	.table-container {
		max-height: 340px;
		overflow-y: auto;
		border: 1px solid #1C1C24;
		border-radius: 6px;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
		font-size: 0.775rem;
	}

	.data-table th {
		background: #050507;
		color: #71717A;
		padding: 0.75rem 1rem;
		font-size: 0.725rem;
		font-weight: 600;
		border-bottom: 1px solid #1C1C24;
		position: sticky;
		top: 0;
		z-index: 2;
	}

	.data-table td {
		padding: 0.65rem 1rem;
		border-bottom: 1px solid #141418;
		color: #A1A1AA;
	}

	.data-table tr:hover {
		background: #0D0D12;
	}

	.horizon-cell {
		color: #FFFFFF;
		font-weight: 600;
	}

	.time-cell {
		color: #71717A;
	}

	.pv-text {
		color: #F59E0B;
	}

	.load-text {
		color: #38BDF8;
	}


	.cell-with-bar {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.bar-track {
		width: 50px;
		height: 3px;
		background: #1C1C24;
		border-radius: 2px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
	}

	.pv-fill {
		background: #F59E0B;
	}

	.cloud-fill {
		background: #71717A;
	}

	.status-tag {
		font-size: 0.7rem;
		padding: 0.15rem 0.45rem;
		border-radius: 4px;
	}

	.status-tag.daylight {
		color: #F59E0B;
		background: rgba(245, 158, 11, 0.12);
		border: 1px solid rgba(245, 158, 11, 0.25);
	}

	.status-tag.night {
		color: #71717A;
		background: #101014;
		border: 1px solid #1C1C24;
	}

	/* Specs Grid */
	.specs-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.spec-card {
		background: #0C0C0F;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.spec-card-title {
		margin: 0;
		font-size: 0.9rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.spec-rows {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		font-size: 0.775rem;
	}

	.spec-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 0.4rem;
		border-bottom: 1px solid #141418;
	}

	.spec-lbl {
		color: #71717A;
	}

	.spec-val {
		color: #FFFFFF;
		font-weight: 500;
	}

	/* Params Grid */
	.params-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.param-box {
		background: #0C0C0F;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.param-category {
		font-size: 0.7rem;
		color: #52525B;
	}

	.param-name {
		margin: 0.15rem 0 0.35rem;
		font-size: 0.9rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.param-description {
		margin: 0;
		font-size: 0.775rem;
		color: #A1A1AA;
		line-height: 1.5;
	}
</style>
