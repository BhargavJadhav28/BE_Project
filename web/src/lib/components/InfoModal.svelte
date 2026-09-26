<script lang="ts">
	interface Props {
		isOpen: boolean;
		onClose: () => void;
	}

	let { isOpen = false, onClose }: Props = $props();

	type TabId = 'workflow' | 'inputs' | 'outputs' | 'glossary';
	let activeTab = $state<TabId>('workflow');

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && isOpen) {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
	<div class="modal-backdrop" onclick={onClose} role="presentation">
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="modal-window"
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			aria-labelledby="modal-title"
			onclick={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div class="modal-header">
				<div>
					<h2 id="modal-title" class="modal-title">System architecture & specifications</h2>
					<p class="modal-subtitle">Autonomous 24-hour microgrid forecasting and dispatch methodology</p>
				</div>
				<button class="close-btn" onclick={onClose} aria-label="Close guide">
					✕
				</button>
			</div>

			<!-- Tabs (Segmented, no misaligned borders) -->
			<div class="modal-tabs">
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'workflow'}
					onclick={() => (activeTab = 'workflow')}
				>Pipeline workflow</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'inputs'}
					onclick={() => (activeTab = 'inputs')}
				>Required feeds</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'outputs'}
					onclick={() => (activeTab = 'outputs')}
				>Forecast envelopes</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'glossary'}
					onclick={() => (activeTab = 'glossary')}
				>Parameters & units</button>
			</div>

			<!-- Body -->
			<div class="modal-body">
				{#if activeTab === 'workflow'}
					<div class="tab-pane">
						<div class="callout-box">
							<h3>Architecture principle (ADR 0001)</h3>
							<p>Origin-anchored horizon conditioning evaluates all 24 future hours simultaneously in under 25 milliseconds on standard CPU. This directly prevents autoregressive drift and compounding multi-step error accumulation.</p>
						</div>

						<div class="workflow-steps">
							<div class="workflow-step">
								<span class="step-num font-mono">01</span>
								<div class="step-text">
									<h4>Self-healing telemetry sanitizer</h4>
									<p>Ingests the 48-hour historical lookback buffer. Telemetry dropouts up to 3 hours caused by packet loss are automatically healed via linear interpolation and nocturnal zero-filling.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">02</span>
								<div class="step-text">
									<h4>Frozen origin anchor & forward weather</h4>
									<p>Observed history is frozen strictly at origin moment T to guarantee zero future data leakage. Combines upcoming 24-hour numerical weather predictions with calendar encodings.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">03</span>
								<div class="step-text">
									<h4>Parallel LightGBM regressor inference</h4>
									<p>Two specialized gradient-boosted decision tree models infer simultaneously: one for solar PV generation and one for facility electrical demand.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">04</span>
								<div class="step-text">
									<h4>Deterministic physical guardrails</h4>
									<p>Physics enforcement guarantees hard 0.0 kW nocturnal solar output when GHI ≤ 0, enforces inverter clipping at 50.0 kW, and binds load demand to [10..45 kW].</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">05</span>
								<div class="step-text">
									<h4>Battery storage economic arbitrage</h4>
									<p>Calculates instantaneous net power (Solar − Load). Solar surplus charges the battery storage; load deficit triggers optimal battery discharge to minimize peak grid tariffs.</p>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'inputs'}
					<div class="tab-pane">
						<div class="split-columns">
							<div class="col-panel">
								<h3>Operator controls</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>Forecast origin (T)</strong>
										<p>The temporal anchor moment. Historical context spans [T-48h..T]; predictions project [T+1h..T+24h].</p>
									</div>
									<div class="feed-item">
										<strong>Scenario presets</strong>
										<p>Seasonal weather archetypes (Summer peak, Winter evening, Spring ramp, Storm front) to stress-test microgrid dynamics.</p>
									</div>
									<div class="feed-item">
										<strong>Dropout simulator</strong>
										<p>Injects synthetic sensor communication blackouts to test automated pipeline self-healing in real time.</p>
									</div>
								</div>
							</div>

							<div class="col-panel">
								<h3>Automated telemetry & weather</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>48-Hour sensor buffer</strong>
										<p>Continuous rolling logs of panel output (kW), building demand (kW), outdoor temperature (°C), and irradiance (W/m²).</p>
									</div>
									<div class="feed-item">
										<strong>24-Hour NWP weather forecast</strong>
										<p>Upcoming numerical predictions of solar irradiance (GHI), ambient temperature (°C), and cloud cover (%).</p>
									</div>
									<div class="feed-item">
										<strong>Cyclical calendar encodings</strong>
										<p>Hour of day, day of week, and day of year to account for facility shifts and occupancy patterns.</p>
									</div>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'outputs'}
					<div class="tab-pane">
						<div class="output-stack">
							<div class="output-card">
								<span class="output-type font-mono">Stream 01</span>
								<h3>Solar PV generation (P̂_pv)</h3>
								<p>Predicted photovoltaic electrical output for each hour of the 24-hour horizon.</p>
								<div class="output-meta font-mono">
									<span>Unit: Kilowatts (kW)</span>
									<span>Rating: 50.0 kW inverter ceiling</span>
									<span>Physics: Strictly 0.0 kW nocturnal zeroing</span>
								</div>
							</div>

							<div class="output-card">
								<span class="output-type font-mono">Stream 02</span>
								<h3>Facility load demand (P̂_load)</h3>
								<p>Predicted building electrical power consumption across equipment, lighting, and HVAC systems.</p>
								<div class="output-meta font-mono">
									<span>Unit: Kilowatts (kW)</span>
									<span>Capacity: 10.0 kW baseload to 45.0 kW peak</span>
									<span>Rhythm: Workday morning ramp and evening domestic draw</span>
								</div>
							</div>

							<div class="output-card">
								<span class="output-type font-mono">Derived schedule</span>
								<h3>Net power & battery schedule</h3>
								<p>Real-time power balance: P̂_net = P̂_pv − P̂_load.</p>
								<div class="output-meta font-mono">
									<span>Surplus: Charges on-site battery storage</span>
									<span>Deficit: Discharges battery or imports grid power</span>
									<span>Energy: 24h integrated sum (kWh) for economic dispatch</span>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'glossary'}
					<div class="tab-pane">
						<div class="table-container font-mono">
							<table class="glossary-table">
								<thead>
									<tr>
										<th>Term</th>
										<th>Unit</th>
										<th>Category</th>
										<th>Operational definition</th>
									</tr>
								</thead>
								<tbody>
									<tr>
										<td><strong>kW (Kilowatt)</strong></td>
										<td>Power</td>
										<td>Metric</td>
										<td>Instantaneous rate of electricity generated or consumed.</td>
									</tr>
									<tr>
										<td><strong>kWh (Kilowatt-hour)</strong></td>
										<td>Energy</td>
										<td>Metric</td>
										<td>Total volume of electrical energy over time (1 kW for 1h = 1 kWh).</td>
									</tr>
									<tr>
										<td><strong>Solar PV (P_pv)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Photovoltaic electrical output. Inverter ceiling: 50.0 kW.</td>
									</tr>
									<tr>
										<td><strong>Load demand (P_load)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Facility electrical consumption. Baseload: 10.0 kW; Peak: 45.0 kW.</td>
									</tr>
									<tr>
										<td><strong>GHI irradiance</strong></td>
										<td>W/m²</td>
										<td>Weather</td>
										<td>Global Horizontal Irradiance: solar intensity per square meter.</td>
									</tr>
									<tr>
										<td><strong>Ambient temperature</strong></td>
										<td>°C</td>
										<td>Weather</td>
										<td>Outdoor air temperature influencing cooling and panel efficiency.</td>
									</tr>
									<tr>
										<td><strong>nMAE accuracy</strong></td>
										<td>%</td>
										<td>SLA Quality</td>
										<td>Normalized Mean Absolute Error relative to capacity. PV: 0.26%, Load: 2.99%.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="modal-footer">
				<button class="return-btn" onclick={onClose}>
					Close guide
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.85);
		backdrop-filter: blur(8px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1.5rem;
	}

	.modal-window {
		background: #09090C;
		border: 1px solid #1C1C24;
		border-radius: 10px;
		width: 100%;
		max-width: 840px;
		max-height: 85vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
		overflow: hidden;
	}

	.modal-header {
		padding: 1.5rem 1.75rem;
		border-bottom: 1px solid #1C1C24;
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
		background: #050507;
	}

	.modal-title {
		margin: 0;
		font-size: 1.15rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.modal-subtitle {
		margin: 0.25rem 0 0;
		font-size: 0.825rem;
		color: #71717A;
	}

	.close-btn {
		background: #141418;
		border: 1px solid #27272A;
		color: #A1A1AA;
		border-radius: 6px;
		width: 30px;
		height: 30px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.close-btn:hover {
		color: #FFFFFF;
		border-color: #3F3F46;
		background: #1C1C22;
	}

	/* Segmented Tab Navigation - Precision Centered Pills */
	.modal-tabs {
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

	.modal-body {
		padding: 1.5rem 1.75rem;
		overflow-y: auto;
		flex: 1;
		background: #09090C;
	}

	.tab-pane {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.callout-box {
		background: #0F0F14;
		border: 1px solid #1C1C24;
		border-left: 3px solid #FFFFFF;
		border-radius: 6px;
		padding: 1rem 1.25rem;
	}

	.callout-box h3 {
		margin: 0 0 0.35rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.callout-box p {
		margin: 0;
		font-size: 0.8rem;
		color: #A1A1AA;
		line-height: 1.5;
	}

	.workflow-steps {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.workflow-step {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		background: #0C0C0F;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 1rem 1.25rem;
	}

	.step-num {
		font-size: 0.85rem;
		font-weight: 700;
		color: #52525B;
		flex-shrink: 0;
	}

	.step-text h4 {
		margin: 0 0 0.25rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.step-text p {
		margin: 0;
		font-size: 0.775rem;
		color: #A1A1AA;
		line-height: 1.45;
	}

	.split-columns {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.col-panel {
		background: #0C0C0F;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.col-panel h3 {
		margin: 0;
		font-size: 0.9rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.feed-list {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.feed-item strong {
		font-size: 0.8rem;
		color: #FFFFFF;
		display: block;
		margin-bottom: 0.15rem;
	}

	.feed-item p {
		margin: 0;
		font-size: 0.75rem;
		color: #A1A1AA;
		line-height: 1.4;
	}

	.output-stack {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.output-card {
		background: #0C0C0F;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
	}

	.output-type {
		font-size: 0.7rem;
		color: #52525B;
	}

	.output-card h3 {
		margin: 0;
		font-size: 0.925rem;
		font-weight: 600;
		color: #FFFFFF;
	}

	.output-card p {
		margin: 0;
		font-size: 0.8rem;
		color: #A1A1AA;
		line-height: 1.45;
	}

	.output-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-top: 0.25rem;
		font-size: 0.725rem;
		color: #71717A;
	}

	.table-container {
		border: 1px solid #1C1C24;
		border-radius: 6px;
		overflow-y: auto;
		max-height: 360px;
	}

	.glossary-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.775rem;
		text-align: left;
	}

	.glossary-table th {
		background: #050507;
		color: #71717A;
		padding: 0.75rem 1rem;
		font-size: 0.725rem;
		font-weight: 600;
		border-bottom: 1px solid #1C1C24;
		position: sticky;
		top: 0;
	}

	.glossary-table td {
		padding: 0.65rem 1rem;
		border-bottom: 1px solid #141418;
		color: #A1A1AA;
	}

	.modal-footer {
		padding: 1rem 1.75rem;
		border-top: 1px solid #1C1C24;
		display: flex;
		justify-content: flex-end;
		background: #050507;
	}

	.return-btn {
		background: #141418;
		border: 1px solid #27272A;
		color: #FFFFFF;
		border-radius: 6px;
		padding: 0.5rem 1.25rem;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.return-btn:hover {
		border-color: #3F3F46;
		background: #1C1C24;
	}
</style>
