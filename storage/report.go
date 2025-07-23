package storage

import (
	"time"

	"gorm.io/gorm"
)

func NewDailyReportStorage(db *gorm.DB) *DailyReport {
	return &DailyReport{
		db: db,
	}
}

type DailyReport struct {
	db *gorm.DB
}

func GetDailyReportByDate(db *gorm.DB, date time.Time) (*DailyReport, error) {
	var report DailyReport
	err := db.Where("date = ?", date).First(&report).Error
	if err != nil {
		return nil, err
	}
	return &report, nil
}

func (dr *DailyReport) Create(report *DailyReport) error {
	return dr.db.Create(report).Error
}
