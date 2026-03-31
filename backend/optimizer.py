class TimeOptimizer:
    @staticmethod
    def calculate_drift_correction(steps, current_index, time_overrun):
        remaining_steps = steps[current_index + 1:]
        if not remaining_steps or time_overrun == 0:
            return steps

        total_remaining_time = sum(s["time_allocated"] for s in remaining_steps)

        for step in remaining_steps:
            proportion = step["time_allocated"] / total_remaining_time
            reduction = int(proportion * time_overrun)

            step["time_allocated"] = max(5, step["time_allocated"] - reduction)

        return steps