/**
 * Component: MetroBeacon
 * Real-time Station Pace Velocity & Ghost Beacon Calculator.
 */
window.MetroBeacon = {
  calculatePace: (dayPassed, totalDays, totalRequired, completedCount) => {
    const targetPace = (dayPassed / totalDays) * totalRequired;
    const deficit = targetPace - completedCount;
    return {
      targetPace,
      deficit: deficit > 0 ? Math.round(deficit * 10) / 10 : 0,
      isBehind: completedCount < targetPace,
      statusText: completedCount < targetPace
        ? `Pace Deficit: -${Math.round(deficit * 10) / 10}`
        : `Pace Velocity: Optimal (+${Math.round((completedCount - targetPace) * 10) / 10})`,
    };
  },
};
