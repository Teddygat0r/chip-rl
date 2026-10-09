include $(dir $(DESIGN_CONFIG))/common.mk
export VERILOG_FILES = $(abspath $(dir $(DESIGN_CONFIG))/../sources/serial.v) $(abspath $(dir $(DESIGN_CONFIG))/../sources/wrapper.v)
