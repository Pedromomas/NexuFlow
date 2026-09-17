/** Session time anchored to a signed server timestamp. No network side effects. */
export class LicenseClock {
  private serverStart: number | null = null;
  private monotonicStart = 0;
  private wallStart = 0;
  private invalid = false;

  constructor(private wall = () => Date.now(), private monotonic = () => performance.now()) {}

  anchor(serverTime: number): void {
    this.serverStart = serverTime;
    this.monotonicStart = this.monotonic();
    this.wallStart = this.wall();
    this.invalid = false;
  }

  now(): number | null {
    if (this.serverStart === null || this.invalid) return null;
    const elapsed = this.monotonic() - this.monotonicStart;
    // Clock edits or sleep where the monotonic clock pauses require a safe refresh.
    if (elapsed < 0 || Math.abs(this.wall() - this.wallStart - elapsed) > 5 * 60_000) {
      this.invalid = true;
      return null;
    }
    return this.serverStart + elapsed;
  }
}
