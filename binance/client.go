package binance

import (
	"context"
	"fmt"
	"strconv"

	binance "github.com/adshao/go-binance/v2"
)

type Client struct {
	client *binance.Client
}

func NewClient(apiKey, secretKey string) *Client {
	return &Client{
		client: binance.NewClient(apiKey, secretKey),
	}
}

func (c *Client) GetTotalBalance() (float64, error) {
	account, err := c.client.NewGetAccountService().Do(context.Background())
	if err != nil {
		return 0, fmt.Errorf("account error: %w", err)
	}

	prices, err := c.client.NewListPricesService().Do(context.Background())
	if err != nil {
		return 0, fmt.Errorf("price error: %w", err)
	}
	priceMap := map[string]float64{}
	for _, p := range prices {
		val, _ := strconv.ParseFloat(p.Price, 64)
		priceMap[p.Symbol] = val
	}

	var totalUSDT float64

	for _, b := range account.Balances {
		free, _ := strconv.ParseFloat(b.Free, 64)
		locked, _ := strconv.ParseFloat(b.Locked, 64)
		total := free + locked
		if total == 0 {
			continue
		}

		var usdtValue float64
		if b.Asset == "USDT" {
			usdtValue = total
		} else {
			symbol := b.Asset + "USDT"
			if price, ok := priceMap[symbol]; ok {
				usdtValue = total * price
			} else {
				symbol = "USDT" + b.Asset
				if price, ok := priceMap[symbol]; ok && price != 0 {
					usdtValue = total / price
				}
			}
		}

		totalUSDT += usdtValue
	}

	return totalUSDT, nil
}
