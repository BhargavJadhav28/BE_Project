<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Helios — 24H Microgrid Forecast & Dispatch</title>
</svelte:head>

<div class="app-viewport">
	<div class="app-container">
		{@render children()}
	</div>
</div>

<style>
	:global(:root) {
		color-scheme: dark;

		/* Warm graphite canvas, paper-white text, one sun-amber accent */
		--bg-base: #0f0e0c;
		--surface: #171512;
		--surface-soft: #1d1b17;
		--surface-sunken: #110f0d;
		--surface-hover: #26231e;
		--thumb: #2b2823;

		/* Hairlines are translucent warm white so they adapt to any surface */
		--hairline: rgba(255, 244, 225, 0.08);
		--hairline-strong: rgba(255, 244, 225, 0.16);

		/* Graphic colors (lines, fills, dots) and readable text variants */
		--color-pv: #f5a524;
		--color-pv-ink: #f7b84b;
		--color-pv-muted: rgba(245, 165, 36, 0.14);

		--color-load: #4da3f0;
		--color-load-ink: #7dbdf5;
		--color-load-muted: rgba(77, 163, 240, 0.14);

		--color-surplus: #2fd39b;
		--color-surplus-ink: #5be0b3;
		--color-surplus-muted: rgba(47, 211, 155, 0.14);

		--color-deficit: #ff5c82;
		--color-deficit-ink: #ff8aa3;
		--color-deficit-muted: rgba(255, 92, 130, 0.14);

		--text-primary: #f4efe6;
		--text-secondary: #b5aea2;
		--text-muted: #8d867a;
		--text-faint: #4e4940;

		/* Primary call-to-action: inverted paper pill */
		--cta-bg: #f4efe6;
		--cta-fg: #14120e;
		--cta-hover: #ffffff;

		--font-sans: 'Hanken Grotesk', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
		--font-mono: 'Spline Sans Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
		--font-display: 'Familjen Grotesk', 'Hanken Grotesk', ui-sans-serif, system-ui, sans-serif;

		/* Concentric radii: shell = core + bezel */
		--radius-core: 22px;
		--radius-inner: 14px;

		/*
		 * "Double bezel": the card itself is the inner core; spread shadows draw the
		 * outer shell tray and its hairline, followed by a deep ambient lift.
		 */
		--bezel:
			inset 0 1px 0 rgba(255, 244, 225, 0.05),
			0 0 0 1px rgba(255, 244, 225, 0.07),
			0 0 0 7px rgba(255, 244, 225, 0.03),
			0 0 0 8px rgba(255, 244, 225, 0.055),
			0 30px 48px -22px rgba(0, 0, 0, 0.75);

		--ease: cubic-bezier(0.32, 0.72, 0, 1);
	}

	:global(*) {
		box-sizing: border-box;
	}

	:global(html) {
		background: var(--bg-base);
		scroll-behavior: smooth;
	}

	:global(body) {
		margin: 0;
		padding: 0;
		background-color: var(--bg-base);
		color: var(--text-primary);
		font-family: var(--font-sans);
		font-variant-numeric: tabular-nums;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		min-height: 100dvh;
		overflow-x: hidden;
	}

	:global(::selection) {
		background: rgba(245, 165, 36, 0.35);
		color: #ffffff;
	}

	/* Data readouts: numbers, timestamps, units */
	:global(.font-mono) {
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
	}

	:global(button) {
		font-family: inherit;
		cursor: pointer;
		user-select: none;
		border: none;
		background: none;
		box-sizing: border-box;
		line-height: inherit;
		color: inherit;
	}

	:global(button:focus-visible),
	:global(input:focus-visible) {
		outline: 2px solid rgba(244, 239, 230, 0.85);
		outline-offset: 2px;
	}

	:global(button:disabled) {
		cursor: not-allowed;
	}

	.app-viewport {
		min-height: 100dvh;
		width: 100%;
		display: flex;
		flex-direction: column;
		/* A faint low-sun glow at the top of the page */
		background:
			radial-gradient(1100px 460px at 50% -10%, rgba(245, 165, 36, 0.12), transparent 70%),
			var(--bg-base);
	}

	.app-container {
		width: 100%;
		min-height: 100dvh;
		display: flex;
		flex-direction: column;
	}

	/* Quiet scrollbar */
	:global(::-webkit-scrollbar) {
		width: 8px;
		height: 8px;
	}

	:global(::-webkit-scrollbar-track) {
		background: transparent;
	}

	:global(::-webkit-scrollbar-thumb) {
		background: rgba(255, 244, 225, 0.16);
		border-radius: 999px;
		border: 2px solid transparent;
		background-clip: padding-box;
	}

	:global(::-webkit-scrollbar-thumb:hover) {
		background: rgba(255, 244, 225, 0.28);
		background-clip: padding-box;
		border: 2px solid transparent;
	}

	@media (prefers-reduced-motion: reduce) {
		:global(html) {
			scroll-behavior: auto;
		}

		:global(*),
		:global(*::before),
		:global(*::after) {
			animation-duration: 0.01ms !important;
			animation-delay: 0ms !important;
			transition-duration: 0.01ms !important;
		}
	}
</style>
