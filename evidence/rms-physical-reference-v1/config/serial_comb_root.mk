include $(dir $(DESIGN_CONFIG))/common.mk
export VERILOG_FILES = $(abspath $(dir $(DESIGN_CONFIG))/../sources/serial_comb_root.v) $(abspath $(dir $(DESIGN_CONFIG))/../sources/wrapper.v)
