package worker

import (
	"log"
	"time"
)

type Worker interface {
	Name() string
	Interval() time.Duration
	Run() error
}

type Runner struct {
	workers []Worker
}

func NewRunner() *Runner {
	return &Runner{workers: []Worker{}}
}

func (r *Runner) Register(w Worker) {
	r.workers = append(r.workers, w)
}

func (r *Runner) Start() {
	for _, w := range r.workers {
		go func(w Worker) {
			ticker := time.NewTicker(w.Interval())
			defer ticker.Stop()

			for {
				err := w.Run()
				if err != nil {
					log.Printf("Error in worker %s: %v", w.Name(), err)
				}
				<-ticker.C
			}
		}(w)
	}
}
