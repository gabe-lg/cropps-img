% Keithley 2400 Current Supply Multi-Mode with Waveform Monitoring
% Israel Gabay 2025 - Cornell
% This code configures the Keithley 2400 to operate in various current supply modes (CC, Step, Ramp, Sine)
% while monitoring and plotting voltage and current values
% Data is stored for post-processing
% IMPORTANT NOTES:
% 1. Ensure the Keithley 2400 is configured for RS-232 via the front panel:
% - Press MENU > COMMUNICATION > INTERFACE: Select RS-232
% - Set Baud Rate: 9600
% - Data Bits: 8
% - Parity: None
% - Stop Bits: 19
% - Terminator: LF
% - FlowKo Control: None
% 2. Use a straight-through RS-232 cable connected to the correct COM port.
% 3. For Sine mode, ensure the instrument supports list mode and has sufficient memory.
% 4. A 100 kΩ resistor is connected as the load.
clear all; close all; clc;
%% Configuration Parameters
% Mode selection (Current supply modes only)
Mode = 'CC'; % Options: 'CC', 'STEP', 'RAMP', 'SINE' - Change this to switch modes
% Measurement settings
VoltCompliance = 200; % Voltage compliance limit [V] for all current modes
MeasurementTime = 60; % Total measurement time [seconds]
SampleInterval = 0.01; % Time between measurements [seconds]
% Mode-specific parameters
BaseCurrent = 20e-6; % Base current [A] (10 µA) for all modes
if strcmp(Mode, 'STEP')
    StepLevels = [5e-6, 1e-5, 1.5e-5]; % Step current levels [A]
elseif strcmp(Mode, 'RAMP')
    RampStart = 0; % Start current [A]
    RampEnd = 2e-5; % End current [A]
elseif strcmp(Mode, 'SINE')
    SineAmplitude = 5e-6; % Amplitude of sine wave [A]
    SineFrequency = 0.1; % Frequency [Hz] (0.1 Hz for 10 cycles in 100s)
end
% Communication settings
ComProtocol = 'COM'; % 'COM' or 'GPIB'
COMPort = 'COM3'; % Change to your actual COM port
% GPIB settings (if using GPIB)
GPIBID = 1; % GPIB interface ID
PAD = 20; % Instrument address
% Data storage
SaveData = true; % Set to true to save data to file
FileName = 'keithley_data'; % Base filename (timestamp will be added)
%% Initialize Communication
fprintf('Initializing Keithley 2400...\n');
switch ComProtocol
    case 'COM'
        keithley = serialport(COMPort, 9600);
        configureTerminator(keithley, "LF");
        keithley.Parity = "none";
        keithley.DataBits = 8;
        keithley.StopBits = 1;
        keithley.FlowControl = "none";
        keithley.Timeout = 10;
    case 'GPIB'
        keithley = gpib('ni', GPIBID, PAD);
        fopen(keithley);
end
% Test communication
if strcmp(ComProtocol, 'COM')
    writeline(keithley, '*IDN?');
    pause(1);
    response = readline(keithley);
else
    fprintf(keithley, '*IDN?\n');
    pause(1);
    response = fscanf(keithley);
end
fprintf('Connected to: %s\n', strtrim(response));
%% Configure Keithley 2400 for Selected Current Mode
fprintf('Configuring for %s mode...\n', Mode);
if strcmp(ComProtocol, 'COM')
    writeline(keithley, '*RST');
else
    fprintf(keithley, '*RST\n');
end
pause(1);
if strcmp(ComProtocol, 'COM')
    writeline(keithley, ':SOUR:FUNC CURR'); % Set to current source for all modes
    writeline(keithley, [':SENS:VOLT:PROT ', num2str(VoltCompliance)]);
    writeline(keithley, ':SENS:VOLT:RANG:AUTO ON');
    writeline(keithley, ':SENS:CURR:RANG:AUTO ON');
    writeline(keithley, ':SENS:FUNC:CONC ON');
    writeline(keithley, ':SENS:FUNC "VOLT"');
    writeline(keithley, ':SENS:FUNC "CURR"');
    writeline(keithley, ':FORM:ELEM VOLT,CURR,TIME');
    writeline(keithley, ':SOUR:DEL:AUTO ON'); % Auto delay for settling
    writeline(keithley, ':TRIG:SOUR BUS'); % Bus trigger for sweep modes
    switch Mode
        case 'CC'
            writeline(keithley, [':SOUR:CURR ', num2str(BaseCurrent)]);
            writeline(keithley, ':TRIG:COUN 1'); % Single measurement per read
            fprintf('Output enabled. Constant current: %.3f mA\n', BaseCurrent * 1000);
        case 'STEP'
            writeline(keithley, ':SOUR:CURR:MODE LIST');
            step_str = num2str(StepLevels, '%.6e,');
            step_str = step_str(1:end-1); % Remove trailing comma
            writeline(keithley, [':SOUR:LIST:CURR ', step_str]);
            writeline(keithley, [':SOUR:LIST:DWEL ', num2str(MeasurementTime / length(StepLevels))]);
            writeline(keithley, ':TRIG:COUN ', num2str(length(StepLevels)));
            fprintf('Output enabled. Step current levels: %s mA\n', num2str(StepLevels * 1000));
        case 'RAMP'
            writeline(keithley, ':SOUR:CURR:MODE SWE');
            writeline(keithley, [':SOUR:CURR:STAR ', num2str(RampStart)]);
            writeline(keithley, [':SOUR:CURR:STOP ', num2str(RampEnd)]);
            num_points = ceil(MeasurementTime / SampleInterval);
            writeline(keithley, [':SOUR:SWE:POIN ', num2str(num_points)]);
            writeline(keithley, ':SOUR:SWE:SPAC LIN');
            writeline(keithley, [':TRIG:COUN ', num2str(num_points)]);
            fprintf('Output enabled. Ramp from %.3f mA to %.3f mA with %d points\n', RampStart * 1000, RampEnd * 1000, num_points);
        case 'SINE'
            writeline(keithley, ':SOUR:CURR:MODE LIST');
            t = 0:SampleInterval:MeasurementTime;
            SineWave = BaseCurrent + SineAmplitude * sin(2 * pi * SineFrequency * t);
            sine_str = num2str(SineWave, '%.6e,');
            sine_str = sine_str(1:end-1); % Remove trailing comma
            writeline(keithley, [':SOUR:LIST:CURR ', sine_str]);
            writeline(keithley, [':SOUR:LIST:DWEL ', num2str(SampleInterval)]);
            writeline(keithley, [':TRIG:COUN ', num2str(length(SineWave))]);
            fprintf('Output enabled. Sine wave around %.3f mA, amplitude %.3f mA\n', BaseCurrent * 1000, SineAmplitude * 1000);
    end
    writeline(keithley, ':OUTP ON');
    if ~strcmp(Mode, 'CC')
        writeline(keithley, ':INIT');
    end
else
    % Similar for GPIB, but skipping for brevity
end
%% Initialize Data Storage and Plotting
NumSamples = ceil(MeasurementTime / SampleInterval);
TimeData = zeros(NumSamples, 1);
VoltageData = zeros(NumSamples, 1);
CurrentData = zeros(NumSamples, 1);
figure('Name', ['Keithley 2400 ', Mode, ' Mode Monitor'], 'Position', [100, 100, 1000, 600]);
subplot(2,1,1);
h_volt = plot(0, 0, 'b-', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('Voltage (V)');
title(['Real-time Voltage - ', Mode, ' Mode']);
grid on;
xlim([0, MeasurementTime]);
volt_ax = gca;
subplot(2,1,2);
h_curr = plot(0, 0, 'r-', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('Current (mA)');
title(['Real-time Current - ', Mode, ' Mode']);
grid on;
xlim([0, MeasurementTime]);
curr_ax = gca;
drawnow;
%% Main Measurement Loop
fprintf('Starting measurements for %.1f seconds...\n', MeasurementTime);
fprintf('Press Ctrl+C to stop early\n\n');
StartTime = tic;
SampleCount = 0;
try
    for i = 1:NumSamples
        if strcmp(Mode, 'CC')
            % Reinforce constant current before each read
            writeline(keithley, [':SOUR:CURR ', num2str(BaseCurrent)]);
            if strcmp(ComProtocol, 'COM')
                writeline(keithley, ':READ?');
                response = readline(keithley);
            else
                fprintf(keithley, ':READ?\n');
                response = fscanf(keithley);
            end
        else
            if strcmp(ComProtocol, 'COM')
                writeline(keithley, '*TRG');
                pause(0.005); % Small delay for settling
                writeline(keithley, ':FETC?');
                response = readline(keithley);
            else
                fprintf(keithley, '*TRG\n');
                pause(0.005);
                fprintf(keithley, ':FETC?\n');
                response = fscanf(keithley);
            end
        end
        data_str = split(response, ",");
        data = str2double(data_str);
        if length(data) >= 2
            SampleCount = SampleCount + 1;
            TimeData(SampleCount) = toc(StartTime);
            VoltageData(SampleCount) = data(1);
            CurrentData(SampleCount) = data(2);
            if mod(SampleCount, 5) == 0 || SampleCount == 1
                set(h_volt, 'XData', TimeData(1:SampleCount), 'YData', VoltageData(1:SampleCount));
                if length(unique(VoltageData(1:SampleCount))) == 1
                    set(volt_ax, 'YLim', [VoltageData(1)*0.9, VoltageData(1)*1.1]);
                else
                    set(volt_ax, 'YLim', [min(VoltageData(1:SampleCount))*0.9, max(VoltageData(1:SampleCount))*1.1]);
                end
                set(h_curr, 'XData', TimeData(1:SampleCount), 'YData', CurrentData(1:SampleCount)*1000);
                if length(unique(CurrentData(1:SampleCount))) == 1
                    set(curr_ax, 'YLim', [CurrentData(1)*900, CurrentData(1)*1100]);
                else
                    set(curr_ax, 'YLim', [min(CurrentData(1:SampleCount))*900, max(CurrentData(1:SampleCount))*1100]);
                end
                drawnow;
            end
            if mod(SampleCount, 50) == 0
                fprintf('Progress: %.1f%% | V=%.3fV | I=%.3fmA\n', ...
                    SampleCount/NumSamples * 100, VoltageData(SampleCount), CurrentData(SampleCount)*1000);
            end
        else
            fprintf('Warning: Invalid response skipped at sample %d\n', i);
        end
        loop_time = toc(StartTime) - TimeData(max(1, SampleCount));
        pause_time = SampleInterval - loop_time;
        if pause_time > 0
            pause(pause_time);
        end
    end
catch ME
    fprintf('\nMeasurement interrupted: %s\n', ME.message);
end
%% Cleanup and Data Saving
fprintf('\nMeasurement completed. Cleaning up...\n');
if strcmp(ComProtocol, 'COM')
    writeline(keithley, ':OUTP OFF');
else
    fprintf(keithley, ':OUTP OFF\n');
end
fprintf('Output disabled.\n');
if strcmp(ComProtocol, 'GPIB')
    fclose(keithley);
end
clear keithley;
fprintf('Connection closed.\n');
TimeData = TimeData(1:SampleCount);
VoltageData = VoltageData(1:SampleCount);
CurrentData = CurrentData(1:SampleCount);
%% Save Data
if SaveData && SampleCount > 0
    timestamp = datestr(now, 'yyyymmdd_HHMMSS');
    fullFileName = [FileName, '_', timestamp, '.mat'];
    MeasurementParams = struct(...
        'Mode', Mode, ...
        'BaseCurrent', BaseCurrent, ...
        'VoltCompliance', VoltCompliance, ...
        'SampleInterval', SampleInterval, ...
        'MeasurementTime', MeasurementTime, ...
        'ActualSamples', SampleCount, ...
        'StartTime', datestr(now));
    save(fullFileName, 'TimeData', 'VoltageData', 'CurrentData', 'MeasurementParams');
    fprintf('Data saved to: %s\n', fullFileName);
    csvFileName = [FileName, '_', timestamp, '.csv'];
    csvData = [TimeData, VoltageData, CurrentData];
    csvwrite(csvFileName, csvData);
    headerFileName = [FileName, '_', timestamp, '_header.txt'];
    fid = fopen(headerFileName, 'w');
    fprintf(fid, 'Keithley 2400 Measurement Data\n');
    fprintf(fid, 'Columns: Time(s), Voltage(V), Current(A)\n');
    fprintf(fid, 'Mode: %s\n', Mode);
    fprintf(fid, 'BaseCurrent: %.6f A\n', BaseCurrent);
    fprintf(fid, 'Voltage Compliance: %.1f V\n', VoltCompliance);
    fprintf(fid, 'Sample Interval: %.3f s\n', SampleInterval);
    fprintf(fid, 'Total Samples: %d\n', SampleCount);
    fclose(fid);
    fprintf('CSV data saved to: %s\n', csvFileName);
end
%% Display Summary Statistics
if SampleCount > 0
    fprintf('\n=== Measurement Summary ===\n');
    fprintf('Total samples: %d\n', SampleCount);
    fprintf('Measurement duration: %.1f s\n', TimeData(end));
    fprintf('Average voltage: %.3f V (±%.3f V)\n', mean(VoltageData), std(VoltageData));
    fprintf('Average current: %.3f mA (±%.3f mA)\n', mean(CurrentData)*1000, std(CurrentData)*1000);
    fprintf('Voltage range: %.3f to %.3f V\n', min(VoltageData), max(VoltageData));
    fprintf('Current range: %.3f to %.3f mA\n', min(CurrentData)*1000, max(CurrentData)*1000);
    avgResistance = mean(VoltageData ./ CurrentData);
    fprintf('Average resistance: %.1f Ω\n', avgResistance);
end
fprintf('\nMeasurement complete!\n');