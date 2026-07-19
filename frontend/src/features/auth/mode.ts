export function isSingleUserMode(): boolean {
	return import.meta.env.SINGLE_USER_MODE === "true";
}