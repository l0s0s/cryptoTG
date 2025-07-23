package model

import (
	"time"
)

type DailyReport struct {
	ID        uint      `gorm:"primaryKey"`
	Date      time.Time `gorm:"index"`
	Balance   float64
	CreatedAt time.Time
}
