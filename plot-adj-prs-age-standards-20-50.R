library(scales)
library(tidyverse)

library(ggplot2)

theme_blog_bw <- function() {
  # Setting base_size to 18-20 ensures text is legible even on mobile
  theme_bw(base_size = 18) %+replace% 
    theme(
      # Bold the title and give it some breathing room
      plot.title = element_text(
        face = "bold", 
        size = rel(1.4), 
        margin = margin(b = 15),
      ),
      plot.subtitle = element_text(hjust = 0.5),
      
      # Darken the axis text for better contrast against the white background
      axis.text = element_text(color = "black", size = rel(0.9)),
      axis.title = element_text(face = "bold"),
      
      # Clean up the legend
      legend.title = element_text(face = "bold"),
      legend.position = "top",
      legend.key = element_blank(),
      
      # Add a bit more padding around the entire plot
      plot.margin = margin(20, 20, 20, 20)
    )
}

# --- Updated Helper with Integer Casting to fix the Error ---
label_duration <- function(x) {
  minutes <- floor(x / 60)
  # round() ensures we have a whole number, as.integer() prevents the sprintf error
  secs <- as.integer(round(x %% 60))
  sprintf("%d:%02d", minutes, secs)
}

age_factors_file_path <- "Downloads/age_factors_2010_5k_20_50yo.csv"
age_factors <- read_csv(age_factors_file_path)

# https://en.wikipedia.org/wiki/List_of_world_records_in_masters_athletics
world_record_5k_age <- tibble(age = c(24, 36, 41, 46, 50), race_time_seconds = c(12 * 60 + 35.36, 12 * 60 + 53.6, 13 * 60 + 6.78, 14 * 60 + 23.6, 14 * 60 + 51.38))

personal_record_seconds <- 15 * 60 + 13
age_factors$age_factor <- with(age_factors, (open_standard_seconds) / age_standard_seconds)

age_factors$personal_record_seconds_adj <- with(age_factors, (personal_record_seconds) / age_factor)

# --- Extracting Exact Coordinates from your Table ---
# PR at age 23
pr_23_val <- age_factors %>% filter(age == 23) %>% pull(personal_record_seconds_adj)
# Adjusted PR at age 37
pr_37_val <- age_factors %>% filter(age == 37) %>% pull(personal_record_seconds_adj)

# --- Plotting ---
age_factors %>% 
  ggplot(mapping = aes(x = age)) +
  # Main Data Lines
  geom_line(mapping = aes(y = age_standard_seconds, color = "Age Standard"), linewidth = 1.5) +
  geom_line(mapping = aes(y = personal_record_seconds_adj, color = "Age-Adjusted PR"), linewidth = 1.5) +
  geom_point(data = world_record_5k_age, mapping = aes(y = race_time_seconds, color = "Current Age World Record")) +
  
  # Vertical markers for Age 23 and 37
  geom_vline(xintercept = c(23, 37), linetype = "dotted", color = "gray40", linewidth = 0.8) +
  
  # Point markers for the PRs
  annotate("point", x = 23, y = pr_23_val, size = 4, shape = 21, fill = "white", stroke = 2) +
  annotate("point", x = 37, y = pr_37_val, size = 4, shape = 21, fill = "white", stroke = 2) +
  
  # Labels - positioned "smartly" above the points
  annotate("label", x = 23, y = pr_23_val + 25, 
           label = paste0("PR @ 23\n", label_duration(pr_23_val)), 
           size = 5, fontface = "bold", label.padding = unit(0.3, "lines")) +
  
  annotate("label", x = 37, y = pr_37_val + 25, 
           label = paste0("Adj. PR @ 37\n", label_duration(pr_37_val)), 
           size = 5, fontface = "bold", label.padding = unit(0.3, "lines")) +
  
  # Scales and Labels
  scale_x_continuous(breaks = seq(20, 50, 5)) +
  scale_y_continuous(labels = label_duration, breaks = seq(700, 1200, 60)) +
  scale_color_manual(values = c("#0072B2", "#D55E00", "#009E73")) +
  theme_blog_bw() +
  labs(
    x = "Age", 
    y = "Race Time (MM:SS)", 
    title = "5,000 Meter Race Performance", 
    subtitle = "2010 Age Standards vs. My Age-Adjusted Personal Record",
    color = NULL
  )
