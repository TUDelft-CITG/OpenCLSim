

from simulation import run_simulation
from analysis import run_analysis


def main():
    print("=" * 60)
    print("FOWT INSTALLATIEKETEN — OpenCLSim simulatie")
    print("=" * 60)
    print()

    result = run_simulation(verbose=True)
    gantt_df, anchors_df = run_analysis(result, show_plots=True)

    return result, gantt_df, anchors_df


if __name__ == "__main__":
    main()
