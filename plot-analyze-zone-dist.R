library(tidyverse)
library(lubridate)

# --- REUSABLE BLOG THEME ---
theme_running_blog <- function() {
  theme_minimal(base_size = 14) +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(), 
      panel.grid.major.y = element_line(color = "grey92"),
      plot.title = element_text(face = "bold", size = 18, margin = margin(b = 10)),
      plot.subtitle = element_text(color = "grey30", margin = margin(b = 20)),
      axis.title = element_text(face = "bold", color = "grey20"),
      axis.text = element_text(color = "grey40"),
      legend.position = "top",
      legend.justification = "left",
      legend.title = element_text(size = 10, face = "bold"),
      legend.text = element_text(size = 9),
      plot.margin = margin(20, 20, 20, 20)
    )
}

# --- DATA PREP ---
raw_data <- read_csv("outputs//processed_running_summary.csv")

# Updated zone levels to match 10% bin increments
zone_levels <- c(
  "Recovery (<60% LT)",
  "Endurance (60-80% LT)",
  "Tempo (80-90% LT)",
  "Threshold (90-110% LT)",
  "VO2 Max (110-120% LT)",
  "Anaerobic (>120% LT)"
)

zone_distribution_weekly <- raw_data |>
  # 1. FIX: Convert raw seconds to minutes
  mutate(minutes = seconds / 60) |>
  # 2. FIX: Filter for new "POWER: " prefix
  filter(str_detect(metric_bin, "^POWER: ")) |>
  # 3. FIX: Handle 'nan' rows if benchmarks were missing
  filter(!str_detect(metric_bin, "nan")) |>
  mutate(
    # Collapse the granular 10% bins into physiological training zones
    training_zone = fct_collapse(metric_bin,
                                 "Recovery (<60% LT)"    = c("POWER: 0-10%", "POWER: 10-20%", "POWER: 20-30%", 
                                                             "POWER: 30-40%", "POWER: 40-50%", "POWER: 50-60%"),
                                 "Endurance (60-80% LT)" = c("POWER: 60-70%", "POWER: 70-80%"),
                                 "Tempo (80-90% LT)"     = "POWER: 80-90%",
                                 "Threshold (90-110% LT)" = c("POWER: 90-100%", "POWER: 100-110%"),
                                 "VO2 Max (110-120% LT)" = "POWER: 110-120%",
                                 "Anaerobic (>120% LT)"  = c("POWER: 120-130%", "POWER: 130-140%", "POWER: 140-150%", 
                                                             "POWER: 150-160%", "POWER: 160-170%", "POWER: 170-180%", 
                                                             "POWER: 180-190%", "POWER: 190-200%")
    ),
    training_zone = fct_relevel(training_zone, zone_levels)
  ) |>
  group_by(week = floor_date(date, unit = "week", week_start = 1), training_zone) |>
  summarise(total_minutes = sum(minutes, na.rm = TRUE), .groups = "drop")

# --- PLOT ---
zone_distribution_weekly |> 
  ggplot(aes(x = week, y = total_minutes, fill = training_zone)) +
  geom_bar(stat = "identity", position = position_stack(), color = "white", linewidth = 0.2) +
  scale_x_date(date_breaks = "1 month", date_labels = "%b %Y") +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.05)), 
    labels = scales::comma
  ) +
  # Warm palette: Red represents the "Hard" Threshold/Anaerobic work
  scale_fill_brewer(palette = "YlOrRd") + 
  labs(
    title = "Weekly Training Intensity Distribution",
    subtitle = "Aggregated from per-second Power data relative to Lactate Threshold",
    x = "Week Starting",
    y = "Total Minutes",
    fill = "INTENSITY ZONE"
  ) +
  theme_running_blog()

# --- DATA PREP (With Completion) ---
plot_data <- zone_distribution_weekly |>
  # 1. Fill in missing weeks/zones with 0 minutes
  complete(
    week = seq(min(week), max(week), by = "1 week"), 
    training_zone = zone_levels, 
    fill = list(total_minutes = 0)
  ) |>
  # 2. Calculate the weekly total AFTER completing the rows
  group_by(week) |>
  mutate(weekly_total = sum(total_minutes, na.rm = TRUE)) |>
  ungroup() |> 
  # 3. Order the levels
  mutate(training_zone = factor(training_zone, levels = zone_levels, ordered = TRUE))

# --- PLOT ---
plot_data |> 
  filter(week > "2025-12-31") |>
  ggplot(aes(x = week)) +
  # Layer 1: The background bar (Total Minutes) - now consistent across all facets
  geom_col(aes(y = weekly_total), fill = "grey90", alpha = 0.8, width = 6) +
  
  # Layer 2: The foreground bar (Zone Minutes)
  geom_col(aes(y = total_minutes, fill = training_zone), show.legend = FALSE, width = 6) +
  
  facet_wrap(~training_zone, ncol = 1) +
  
  scale_x_date(date_breaks = "1 month", date_labels = "%b %Y") +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.05)), 
    labels = scales::comma
  ) +
  scale_fill_brewer(palette = "YlOrRd") + 
  labs(
    title = "Weekly Volume Distribution by Zone",
    subtitle = "Grey bars represent total volume; colored bars represent time in specific zone",
    x = "Week Starting",
    y = "Minutes"
  ) +
  theme_running_blog() +
  theme(
    strip.text = element_text(face = "bold", hjust = 0),
    strip.background = element_blank(),
    panel.spacing = unit(1.2, "lines")
  )


zone_distribution_weekly |> 
  group_by(week) |> 
  mutate(total_minutes_week = sum(total_minutes)) |> 
  ungroup() |> 
  mutate(training_zone_frac = total_minutes / total_minutes_week) |> 
  group_by(training_zone) |> 
  summarise(mean_zone_frac = mean(training_zone_frac),
            median_zone_frac = median(training_zone_frac),
            max_zone_frac = max(training_zone_frac),
            min_zone_frac = min(training_zone_frac), 
            sd_zone_frac = sd(training_zone_frac),
            perc25_zone_frac = quantile(training_zone_frac, .25),
            perc75_zone_frac = quantile(training_zone_frac, .75))

zone_distribution_weekly |> 
  write_csv("outputs/zone_distribution_weekly.csv")
