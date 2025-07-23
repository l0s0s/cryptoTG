package service

import (
	"time"

	"github.com/l0s0s/cryptoTG/model"
)

type ReportStorage interface {
	GetDailyReportByDate(date time.Time) (*model.DailyReport, error)
	Create(report *model.DailyReport) error
}

func NewReporter(storage ReportStorage) *Reporter {
	return &Reporter{
		storage: storage,
	}
}

type Reporter struct {
	storage ReportStorage
}

func (r *Reporter) SaveTodayBalance(balance float64) error {
	today := time.Now().Truncate(24 * time.Hour)
	report := model.DailyReport{
		Date:    today,
		Balance: balance,
	}

	return r.storage.Create(&report)
}

func (r *Reporter) GetYesterdayBalance() (float64, error) {
	yesterday := time.Now().Add(-24 * time.Hour).Truncate(24 * time.Hour)
	report, err := r.storage.GetDailyReportByDate(yesterday)
	if err != nil {
		return 0, err
	}

	return report.Balance, nil
}
