package worker

import (
	"time"
)

type Client interface {
	GetTotalBalance() (float64, error)
}

type Reporter interface {
	SaveTodayBalance(balance float64) error
	GetYesterdayBalance() (float64, error)
}

type DailyReporterWorker struct {
	client   Client
	reporter Reporter
}

func NewDailyReporterWorker(client Client, reporter Reporter) *DailyReporterWorker {
	return &DailyReporterWorker{
		client:   client,
		reporter: reporter,
	}
}

func (d DailyReporterWorker) Name() string {
	return "DailyReporter"
}

func (d DailyReporterWorker) Interval() time.Duration {
	return 24 * time.Hour
}

func (d DailyReporterWorker) Run() error {
	balance, err := d.client.GetTotalBalance()
	if err != nil {
		return err
	}

	if err := d.reporter.SaveTodayBalance(balance); err != nil {
		return err
	}

	return nil
}
