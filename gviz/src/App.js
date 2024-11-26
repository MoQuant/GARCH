import React, { Component, Fragment } from 'react'
import Plot from 'react-plotly.js'

export default class App extends Component {

  constructor(){
    super()

    this.state = {
      response: null,
      progress: 'Waiting for Forecast',
      ticker: 'AAPL',
      sock: null,
      fn: 30,
      paths: 50,
      steps: 500,
      days: 1.0
    }

    this.changeTicker = this.changeTicker.bind(this)
    this.clickButton = this.clickButton.bind(this)
    this.plotData = this.plotData.bind(this)
  }

  componentDidMount(){
    const socket = new WebSocket("ws://localhost:8080")
    socket.onmessage = (evt) => {
      const resp = JSON.parse(evt.data)
      if(resp['type'] == 'message'){
        this.setState({ progress: resp['payload'] })
      }
      if(resp['type'] == 'graph'){
        this.setState({ response: resp['payload'] })
      }
    }
    this.setState({ sock: socket})
  }

  clickButton(evt){
    const { ticker, sock, fn, paths, steps, days } = this.state
    const message = JSON.stringify([ticker, fn, paths, steps, days])
    sock.send(message)
    evt.preventDefault()
  }

  changeTicker(evt){
    this.setState({ [evt.target.name]: evt.target.value })
  }

  plotData(){
    const { response } = this.state
    const hold = []
    if(response !== null){
      hold.push(
        <Plot
          data={[{
            x: response['x'],
            y: response['y'],
            type: 'lines',
            marker: {
              color: 'limegreen'
            }
          }]}
          layout={{
            title: "GARCH(1,1) Model For " + this.state.ticker
          }}
        />
      )
      hold.push(
        <Plot
          data={[{
            x: response['x2'],
            y: response['y2'],
            type:'lines',
            marker:{
              color: 'blue'
            }
          }]}
          layout={{
            title: "Stock Price Simulation for " + this.state.ticker + " | Current Price: " + response['price']
          }}
        />
      )
    }
    return hold 
  }

  render(){

    return(
      <Fragment>
        <center>
          <div style={{backgroundColor: 'black', color:'limegreen',fontSize:25}}>GARCH Model Forecaster</div>
          <br/>
          <br/>
          <div>Enter your stock ticker</div>
          <div><input name="ticker" style={{backgroundColor:'black', color:'limegreen', textAlign:'center', fontSize: 16}}value={this.state.ticker} onChange={this.changeTicker}/></div>
          <div>Enter your forecast size</div>
          <div><input name="fn" style={{backgroundColor:'black', color:'limegreen', textAlign:'center', fontSize: 16}}value={this.state.fn} onChange={this.changeTicker}/></div>
          <div>Enter your number of paths</div>
          <div><input name="paths" style={{backgroundColor:'black', color:'limegreen', textAlign:'center', fontSize: 16}}value={this.state.paths} onChange={this.changeTicker}/></div>
          <div>Enter your number of steps</div>
          <div><input name="steps" style={{backgroundColor:'black', color:'limegreen', textAlign:'center', fontSize: 16}}value={this.state.steps} onChange={this.changeTicker}/></div>
          <div>Enter the number of days</div>
          <div><input name="days" style={{backgroundColor:'black', color:'limegreen', textAlign:'center', fontSize: 16}}value={this.state.days} onChange={this.changeTicker}/></div>
          
          <br/>
          <div><button onClick={this.clickButton}>Fetch Forecast</button></div>
          <br/>
          <div>{this.state.progress}</div>
          <br/>
          <div>{this.plotData()}</div>
        </center>
      </Fragment>
    )
  }


}