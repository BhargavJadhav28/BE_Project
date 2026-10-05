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
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	/* Segmented tab track */
	.drawer-tabs {
		display: flex;
		align-items: center;
		gap: 2px;
		width: fit-content;
		max-width: calc(100% - 4rem);
		margin: 1.5rem 2rem 0;
		padding: 3px;
		background: var(--surface-sunken);
		border-radius: 999px;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.drawer-tabs::-webkit-scrollbar {
		display: none;
	}

	.tab-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: 34px;
		padding: 0 1rem;
		background: transparent;
		color: var(--text-secondary);
		font-family: var(--font-sans);
		font-size: 0.78rem;
		font-weight: 500;
		line-height: 1;
		white-space: nowrap;
		border-radius: 999px;
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			box-shadow 0.4s var(--ease);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		background: var(--surface);
		color: var(--text-primary);
		box-shadow:
			0 0 0 1px var(--hairline),
			0 2px 6px -2px rgba(23, 21, 15, 0.16);
	}

	.drawer-body {
		padding: 1.5rem 2rem 2rem;
	}

	.table-container {
		max-height: 340px;
		overflow-y: auto;
		border-radius: var(--radius-inner);
		box-shadow: inset 0 0 0 1px var(--hairline);
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
		font-size: 0.78rem;
	}

	.data-table th {
		background: var(--surface-soft);
		color: var(--text-muted);
		padding: 0.8rem 1rem;
		font-family: var(--font-sans);
		font-size: 0.66rem;
		font-weight: 500;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		white-space: nowrap;
		border-bottom: 1px solid var(--hairline);
		position: sticky;
		top: 0;
		z-index: 2;
	}

	.data-table td {
		padding: 0.7rem 1rem;
		border-bottom: 1px solid var(--hairline);
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.data-table tr:last-child td {
		border-bottom: none;
	}

	.data-table tbody tr {
		transition: background-color 0.3s var(--ease);
	}

	.data-table tbody tr:hover {
		background: var(--surface-soft);
	}

	.horizon-cell {
		color: var(--text-primary) !important;
		font-weight: 500;
	}

	.time-cell {
		color: var(--text-muted) !important;
	}

	.pv-text {
		color: var(--color-pv-ink) !important;
	}

	.load-text {
		color: var(--color-load-ink) !important;
	}

	.surplus-text {
		color: var(--color-surplus-ink);
	}

	.cell-with-bar {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.bar-track {
		width: 56px;
		height: 4px;
		background: var(--surface-sunken);
		border-radius: 999px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 999px;
	}

	.pv-fill {
		background: var(--color-pv);
	}

	.cloud-fill {
		background: rgba(255, 244, 225, 0.28);
	}

	.status-tag {
		display: inline-flex;
		font-family: var(--font-sans);
		font-size: 0.7rem;
		font-weight: 500;
		padding: 0.15rem 0.65rem;
		border-radius: 999px;
	}

	.status-tag.daylight {
		color: var(--color-pv-ink);
		background: var(--color-pv-muted);
	}

	.status-tag.night {
		color: var(--text-muted);
		background: var(--surface-sunken);
	}

	/* Specs */
	.specs-grid,
	.params-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.spec-card,
	.param-box {
		background: var(--surface-soft);
		box-shadow: inset 0 0 0 1px var(--hairline);
		border-radius: 18px;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
	}

	.spec-card {
		gap: 1.1rem;
	}

	.spec-card-title,
	.param-name {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.spec-rows {
		display: flex;
		flex-direction: column;
		font-size: 0.78rem;
	}

	.spec-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		padding: 0.65rem 0;
		border-top: 1px solid var(--hairline);
	}

	.spec-lbl {
		font-family: var(--font-sans);
		color: var(--text-muted);
	}

	.spec-val {
		color: var(--text-primary);
		font-weight: 500;
		text-align: right;
	}

	/* Params */
	.param-box {
		gap: 0.45rem;
	}

	.param-category {
		font-family: var(--font-sans);
		font-size: 0.66rem;
		font-weight: 500;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	.param-name {
		margin-top: 0.1rem;
	}

	.param-description {
		margin: 0;
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	@media (max-width: 760px) {
		.drawer-tabs {
			margin-inline: 1.25rem;
			max-width: calc(100% - 2.5rem);
		}

		.drawer-body {
			padding-inline: 1.25rem;
		}
	}
</style>
